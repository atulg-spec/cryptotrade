"""
stream_forex  —  Django management command
============================================
Streams real-time Forex & Commodity prices from Finnhub WebSocket API
and persists them in the Stock model.

Usage
-----
    python manage.py stream_forex
    python manage.py stream_forex --dry-run       # print symbols and exit
    python manage.py stream_forex --workers 4     # override worker count

Settings
--------
    FINNHUB_API_KEY = "your_key_here"   # in settings.py or as env var

Architecture
------------
  Symbols are split into chunks of MAX_SUBS_PER_SOCKET (default 50).
  Each chunk gets its own long-lived asyncio task running a dedicated
  WebSocket connection to wss://ws.finnhub.io.
  The Finnhub free tier supports up to 50 simultaneous subscriptions per
  connection; the chunking makes it trivial to scale to hundreds of symbols.

  Every FLUSH_INTERVAL seconds each worker flushes its in-memory price
  buffer to the DB via a bulk_update — the same battle-tested pattern used
  in the existing Binance stream command.
"""

import asyncio
import json
import logging
import os
from decimal import Decimal, InvalidOperation
from itertools import islice

import websockets
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stockmanagement.models import Stock

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FINNHUB_WS_URL = "wss://ws.finnhub.io"
MAX_SUBS_PER_SOCKET = 50   # Finnhub free-tier limit per connection
FLUSH_INTERVAL = 1.0       # seconds between DB flushes
RECONNECT_BASE_DELAY = 3   # seconds (doubles on repeated failures, max 60s)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Symbol master lists
# ---------------------------------------------------------------------------

# Finnhub uses the OANDA broker prefix for forex/metal symbols.
# Format: "OANDA:<BASE>_<QUOTE>"

FOREX_SYMBOLS = [
    # ── 15 Majors & Common Crosses ──────────────────────────────────────────
    "OANDA:EUR_USD", "OANDA:GBP_USD", "OANDA:USD_JPY", "OANDA:USD_CHF",
    "OANDA:AUD_USD", "OANDA:USD_CAD", "OANDA:NZD_USD",
    "OANDA:EUR_GBP", "OANDA:EUR_JPY", "OANDA:EUR_AUD",
    "OANDA:EUR_CAD", "OANDA:EUR_CHF", "OANDA:GBP_JPY",
    "OANDA:GBP_AUD", "OANDA:GBP_CAD",
    
    # ── 15 Minors & Exotics ─────────────────────────────────────────────────
    "OANDA:AUD_JPY", "OANDA:AUD_CAD", "OANDA:AUD_CHF",
    "OANDA:NZD_JPY", "OANDA:NZD_CAD", "OANDA:CAD_JPY",
    "OANDA:CHF_JPY", "OANDA:USD_SGD", "OANDA:USD_HKD",
    "OANDA:USD_MXN", "OANDA:USD_ZAR", "OANDA:USD_TRY",
    "OANDA:USD_NOK", "OANDA:USD_SEK", "OANDA:USD_PLN",
    
    # ── 5 More Exotics ──────────────────────────────────────────────────────
    "OANDA:USD_HUF", "OANDA:USD_CZK", "OANDA:USD_CNH",
    "OANDA:USD_THB", "OANDA:SGD_JPY"
]

# Total FOREX = 35 symbols

# Precious metals and some commodities use OANDA conventions.
COMMODITY_SYMBOLS = [
    # ── 10 Metals & Energies ───────────────────────────────────────────────
    "OANDA:XAU_USD",   # Gold
    "OANDA:XAG_USD",   # Silver
    "OANDA:XPT_USD",   # Platinum
    "OANDA:XPD_USD",   # Palladium
    "OANDA:XCU_USD",   # Copper
    "OANDA:BCO_USD",   # Brent Crude Oil
    "OANDA:CORN_USD",  # Corn
    "OANDA:WHEAT_USD", # Wheat
    "OANDA:SOYBN_USD", # Soybeans
    "OANDA:SUGAR_USD", # Sugar
]

# Total COMMODITIES = 10 symbols
# TOTAL = 45 symbols (Leaves 5 buffer slots for web frontend testing on the free tier)


ALL_SYMBOLS = FOREX_SYMBOLS + COMMODITY_SYMBOLS

# Human-readable names for DB seeding
_DISPLAY_NAMES = {
    # Majors
    "OANDA:EUR_USD": "Euro / US Dollar",
    "OANDA:GBP_USD": "Pound Sterling / US Dollar",
    "OANDA:USD_JPY": "US Dollar / Japanese Yen",
    "OANDA:USD_CHF": "US Dollar / Swiss Franc",
    "OANDA:AUD_USD": "Australian Dollar / US Dollar",
    "OANDA:USD_CAD": "US Dollar / Canadian Dollar",
    "OANDA:NZD_USD": "New Zealand Dollar / US Dollar",
    # Metals & Commodities
    "OANDA:XAU_USD": "Gold / US Dollar",
    "OANDA:XAG_USD": "Silver / US Dollar",
    "OANDA:XPT_USD": "Platinum / US Dollar",
    "OANDA:XPD_USD": "Palladium / US Dollar",
    "OANDA:XCU_USD": "Copper / US Dollar",
    "OANDA:BCO_USD": "Brent Crude Oil",
    "OANDA:WTI_USD": "WTI Crude Oil",
    "OANDA:NG_USD":  "Natural Gas",
    "OANDA:CORN_USD":   "Corn",
    "OANDA:WHEAT_USD":  "Wheat",
    "OANDA:SOYBN_USD":  "Soybeans",
    "OANDA:SUGAR_USD":  "Sugar",
    "OANDA:COTTON_USD": "Cotton",
    "OANDA:COFFEE_USD": "Coffee",
    "OANDA:ALU_USD":  "Aluminium",
    "OANDA:NI_USD":   "Nickel",
    "OANDA:ZNC_USD":  "Zinc",
    "OANDA:LEAD_USD": "Lead",
}


def _display_name(symbol: str) -> str:
    """Return a friendly name for a symbol, falling back to reformatting the raw symbol."""
    if symbol in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[symbol]
    # e.g. "OANDA:GBP_JPY" → "GBP / JPY"
    parts = symbol.split(":")
    if len(parts) == 2:
        pair = parts[1].replace("_", " / ")
        return pair
    return symbol


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunked(iterable, size):
    """Split an iterable into fixed-size chunks."""
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            return
        yield chunk


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


# ---------------------------------------------------------------------------
# Django Management Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Stream real-time Forex & Commodity prices from Finnhub WebSocket "
        "into the Stock model. Requires FINNHUB_API_KEY in settings.py."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print all symbols and exit without connecting to Finnhub.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=None,
            help=(
                f"Override the number of WebSocket workers "
                f"(default: auto — one per {MAX_SUBS_PER_SOCKET}-symbol chunk)."
            ),
        )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        self.api_key = (
            getattr(settings, "FINNHUB_API_KEY", None)
            or os.environ.get("FINNHUB_API_KEY", "")
        )

        if options["dry_run"]:
            self._dry_run()
            return

        if not self.api_key:
            raise CommandError(
                "❌  FINNHUB_API_KEY is not set.\n"
                "    Add it to settings.py:  FINNHUB_API_KEY = 'your_key_here'\n"
                "    Get a free key at https://finnhub.io/register"
            )

        asyncio.run(self.main(options))

    def _dry_run(self):
        self.stdout.write(self.style.SUCCESS(
            f"\n📋  Dry-run: {len(ALL_SYMBOLS)} symbols across "
            f"{len(list(chunked(ALL_SYMBOLS, MAX_SUBS_PER_SOCKET)))} worker(s)\n"
        ))
        for i, (cat, syms) in enumerate([("🌍  FOREX", FOREX_SYMBOLS), ("⛏️   COMMODITIES", COMMODITY_SYMBOLS)]):
            self.stdout.write(f"\n{cat} ({len(syms)} symbols)")
            self.stdout.write("-" * 45)
            for s in syms:
                self.stdout.write(f"  {s:<28}  {_display_name(s)}")
        self.stdout.write("")

    # ------------------------------------------------------------------
    # Async main
    # ------------------------------------------------------------------

    async def main(self, options):
        self.stdout.write(self.style.HTTP_INFO(
            f"\n🌐  Finnhub Forex & Commodity Streamer"
        ))
        self.stdout.write(
            f"📊  {len(FOREX_SYMBOLS)} forex pairs + "
            f"{len(COMMODITY_SYMBOLS)} commodities = "
            f"{len(ALL_SYMBOLS)} total symbols"
        )

        # Seed all symbols into the DB so FK references are always valid
        self.stdout.write("💾  Seeding assets into DB …")
        await self.seed_assets(ALL_SYMBOLS)
        self.stdout.write(self.style.SUCCESS("✅  Asset seed complete"))

        # Build one task per chunk
        chunks = list(chunked(ALL_SYMBOLS, MAX_SUBS_PER_SOCKET))
        worker_limit = options.get("workers") or len(chunks)
        active_chunks = chunks[:worker_limit]

        self.stdout.write(
            f"🔌  Spawning {len(active_chunks)} WebSocket worker(s) "
            f"({MAX_SUBS_PER_SOCKET} symbols each) …\n"
        )

        tasks = [
            asyncio.create_task(self.websocket_worker(idx + 1, chunk))
            for idx, chunk in enumerate(active_chunks)
        ]

        await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # DB seeding  (sync_to_async so we stay off the event-loop thread)
    # ------------------------------------------------------------------

    @sync_to_async
    def seed_assets(self, symbols):
        objs = [
            Stock(
                symbol=sym,
                name=_display_name(sym),
                current_price=Decimal("0"),
                open_price=Decimal("0"),
                high_price=Decimal("0"),
                low_price=Decimal("0"),
                close_price=Decimal("0"),
                volume=0,
            )
            for sym in symbols
        ]
        with transaction.atomic():
            created = Stock.objects.bulk_create(objs, ignore_conflicts=True)
        logger.info(f"Seeded {len(created)} new Stock rows (existing rows untouched).")

    # ------------------------------------------------------------------
    # WebSocket worker  (one per chunk of symbols)
    # ------------------------------------------------------------------

    async def websocket_worker(self, worker_id: int, symbols: list):
        """
        Connects to Finnhub, subscribes to `symbols`, buffers incoming ticks,
        and flushes to the DB every FLUSH_INTERVAL seconds.
        Reconnects automatically with exponential back-off on any error.
        """
        ws_url = f"{FINNHUB_WS_URL}?token={self.api_key}"
        label = f"[Worker {worker_id}]"
        self.stdout.write(f"🔗  {label} → {len(symbols)} symbols")

        delay = RECONNECT_BASE_DELAY

        while True:
            buffer: dict[str, dict] = {}
            last_flush: float = asyncio.get_event_loop().time()

            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=10 * 1024 * 1024,  # 10 MB
                ) as ws:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅  {label} connected")
                    )
                    delay = RECONNECT_BASE_DELAY  # reset back-off on success

                    # Subscribe to all symbols in this chunk
                    for sym in symbols:
                        await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        msg_type = msg.get("type")

                        if msg_type == "trade":
                            # Finnhub trade tick: {"type":"trade","data":[{"s":"OANDA:EUR_USD","p":1.08,"t":...,"v":...}]}
                            for tick in msg.get("data", []):
                                sym = tick.get("s")
                                price = tick.get("p")
                                if sym and price is not None:
                                    # Accumulate last known price per symbol
                                    buffer[sym] = {
                                        "price": _to_decimal(price),
                                        "volume": int(tick.get("v", 0)),
                                    }

                        elif msg_type == "error":
                            logger.warning(f"{label} Finnhub error: {msg.get('msg')}")

                        elif msg_type == "ping":
                            await ws.send(json.dumps({"type": "pong"}))

                        # Periodic flush
                        now = asyncio.get_event_loop().time()
                        if now - last_flush >= FLUSH_INTERVAL and buffer:
                            snapshot = dict(buffer)
                            await self.flush_prices(snapshot)
                            buffer.clear()
                            last_flush = now

            except websockets.exceptions.ConnectionClosedOK:
                logger.info(f"{label} connection closed cleanly — reconnecting …")

            except websockets.exceptions.ConnectionClosedError as exc:
                logger.warning(f"{label} connection error: {exc} — reconnecting in {delay}s …")

            except Exception:
                logger.exception(f"{label} unexpected crash — reconnecting in {delay}s …")

            self.stdout.write(
                f"⚠️   {label} disconnected — retrying in {delay}s …"
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)   # exponential back-off, cap at 60s

    # ------------------------------------------------------------------
    # DB flush  (bulk_update to minimise round-trips)
    # ------------------------------------------------------------------

    @sync_to_async
    def flush_prices(self, price_map: dict):
        """
        Fetch matching Stock rows, apply latest prices, bulk_update.
        Runs in a thread pool managed by sync_to_async.
        """
        if not price_map:
            return

        assets = list(Stock.objects.filter(symbol__in=price_map.keys()))
        if not assets:
            return

        for asset in assets:
            data = price_map[asset.symbol]
            new_price = data["price"]

            # Derive change & percentage from the stored open_price
            if asset.open_price and asset.open_price > 0:
                change = new_price - asset.open_price
                change_pct = (change / asset.open_price) * 100
            else:
                # If no open price yet, treat the first tick as the "open"
                asset.open_price = new_price
                change = Decimal("0")
                change_pct = Decimal("0")

            asset.current_price = new_price
            asset.price_change = change.quantize(Decimal("0.00001"))
            asset.percentage_change = change_pct.quantize(Decimal("0.00001"))

            if data["volume"]:
                asset.volume = data["volume"]

        Stock.objects.bulk_update(
            assets,
            ["current_price", "open_price", "price_change", "percentage_change", "volume"],
        )
        logger.debug(f"Flushed {len(assets)} prices to DB")
