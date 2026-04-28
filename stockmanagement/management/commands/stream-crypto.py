import json
import signal
import threading
import time
import logging
from decimal import Decimal, InvalidOperation

import websocket
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="
BULK_UPDATE_INTERVAL = 0.5
RECONNECT_DELAY = 5


# ──────────────────────────────────────────────────────────────
# Thread Safe Price Buffer
# ──────────────────────────────────────────────────────────────

class PriceBuffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.buffer = {}

    def update(self, symbol, data):
        with self.lock:
            self.buffer.setdefault(symbol, {}).update(data)

    def flush(self):
        with self.lock:
            snap = dict(self.buffer)
            self.buffer.clear()
            return snap


# ──────────────────────────────────────────────────────────────
# Binance Websocket Worker
# ──────────────────────────────────────────────────────────────

class BinanceStreamWorker(threading.Thread):

    def __init__(self, symbols, buffer, worker_id, stop_event, debug=False):
        super().__init__(daemon=True)
        self.symbols = symbols
        self.buffer = buffer
        self.worker_id = worker_id
        self.stop_event = stop_event
        self.debug = debug
        self.ws = None

    def build_url(self):
        streams = []
        for s in self.symbols:
            s = s.lower()
            streams.append(f"{s}@trade")
            streams.append(f"{s}@miniTicker")
        return BINANCE_WS_BASE + "/".join(streams)

    def on_message(self, ws, message):
        try:
            payload = json.loads(message)
            data = payload.get("data", payload)
            event = data.get("e")

            if event == "trade":
                symbol = data["s"]
                price = data["p"]
                self.buffer.update(symbol, {"current_price": price})

                if self.debug:
                    logger.info("TRADE %s %s", symbol, price)

            elif event == "24hrMiniTicker":
                symbol = data["s"]

                self.buffer.update(
                    symbol,
                    {
                        "mini_close": data.get("c"),
                        "open_price": data.get("o"),
                        "high_price": data.get("h"),
                        "low_price": data.get("l"),
                        "quote_volume_24h": data.get("q"),
                    },
                )

                if self.debug:
                    logger.info("MINI %s %s", symbol, data.get("c"))

        except Exception as e:
            logger.error("Parse error %s", e)

    def on_open(self, ws):
        logger.info(
            "[Worker %d] Connected streaming %d symbols",
            self.worker_id,
            len(self.symbols),
        )

    def on_close(self, ws, code, msg):
        logger.info("[Worker %d] Closed", self.worker_id)

    def run(self):
        while not self.stop_event.is_set():
            url = self.build_url()

            self.ws = websocket.WebSocketApp(
                url,
                on_message=self.on_message,
                on_open=self.on_open,
                on_close=self.on_close,
            )

            self.ws.run_forever()

            if self.stop_event.is_set():
                break

            logger.info("Reconnect in %s sec", RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)

    def stop(self):
        if self.ws:
            self.ws.close()


# ──────────────────────────────────────────────────────────────
# DB Flush Worker
# ──────────────────────────────────────────────────────────────

class DBFlushWorker(threading.Thread):

    def __init__(self, buffer, stop_event, dry_run=False, debug=False):
        super().__init__(daemon=True)
        self.buffer = buffer
        self.stop_event = stop_event
        self.dry_run = dry_run
        self.debug = debug
        self.total_updates = 0

    def dec(self, val):
        try:
            return Decimal(str(val))
        except (InvalidOperation, TypeError):
            return Decimal("0")

    def flush(self):
        from stockmanagement.models import Stock

        snap = self.buffer.flush()

        if not snap:
            return

        stocks = {
            s.symbol: s
            for s in Stock.objects.filter(symbol__in=list(snap.keys()))
        }

        updated = []

        for symbol, data in snap.items():
            stock = stocks.get(symbol)
            if not stock:
                continue

            price = data.get("current_price") or data.get("mini_close")

            if price:
                stock.current_price = self.dec(price)

            if data.get("open_price"):
                stock.open_price = self.dec(data["open_price"])

            if data.get("high_price"):
                stock.high_price = self.dec(data["high_price"])

            if data.get("low_price"):
                stock.low_price = self.dec(data["low_price"])

            if stock.open_price and stock.open_price > 0:
                stock.price_change = stock.current_price - stock.open_price
                stock.percentage_change = (
                    stock.price_change / stock.open_price
                ) * 100

            stock.last_updated = timezone.now()
            updated.append(stock)

        if not updated:
            return

        if self.dry_run:
            logger.info("[DRY RUN] %d records", len(updated))
        else:
            with transaction.atomic():
                Stock.objects.bulk_update(
                    updated,
                    [
                        "current_price",
                        "open_price",
                        "high_price",
                        "low_price",
                        "price_change",
                        "percentage_change",
                        "last_updated",
                    ],
                )

        self.total_updates += len(updated)

    def run(self):
        while not self.stop_event.is_set():
            time.sleep(BULK_UPDATE_INTERVAL)
            self.flush()


# ──────────────────────────────────────────────────────────────
# Management Command
# ──────────────────────────────────────────────────────────────

class Command(BaseCommand):

    help = "Stream crypto prices from Binance"

    def add_arguments(self, parser):
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def get_symbols(self):
        from stockmanagement.models import Stock

        symbols = list(
            Stock.objects.filter(exchange__iexact="CRYPTO")
            .values_list("symbol", flat=True)
        )

        if not symbols:
            default_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

            stocks = [
                Stock(symbol=s, exchange="CRYPTO")
                for s in default_symbols
            ]

            Stock.objects.bulk_create(stocks, ignore_conflicts=True)

            logger.info("Auto-created default symbols")

            return default_symbols

        return symbols

    def handle(self, *args, **options):

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

        debug = options["debug"]
        dry_run = options["dry_run"]

        symbols = self.get_symbols()

        stop_event = threading.Event()
        buffer = PriceBuffer()

        ws_workers = []

        db_worker = DBFlushWorker(buffer, stop_event, dry_run, debug)
        db_worker.start()

        for i, sym in enumerate(symbols):
            worker = BinanceStreamWorker(
                [sym],
                buffer,
                i,
                stop_event,
                debug,
            )
            worker.start()
            ws_workers.append(worker)
            time.sleep(0.2)

        def shutdown(sig, frame):
            print("Stopping...")
            stop_event.set()

        signal.signal(signal.SIGINT, shutdown)

        while not stop_event.is_set():
            time.sleep(1)

        for w in ws_workers:
            w.stop()

        print("Total updates:", db_worker.total_updates)