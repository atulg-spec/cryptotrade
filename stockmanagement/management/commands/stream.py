import asyncio
import json
import logging
from decimal import Decimal
from itertools import islice

import requests
import websockets
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.db import transaction

from stockmanagement.models import Stock

BINANCE_REST_URL = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

MAX_STREAMS_PER_SOCKET = 300
WORKER_COUNT = 3
FLUSH_INTERVAL = 1.0  # seconds

logger = logging.getLogger(__name__)


# ---------------------------
# Helpers
# ---------------------------

def chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            return
        yield chunk


def get_tradable_symbols():
    res = requests.get(BINANCE_REST_URL, timeout=15)
    res.raise_for_status()
    data = res.json()

    return [
        s for s in data["symbols"]
        if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
    ]


# ---------------------------
# Django Command
# ---------------------------

class Command(BaseCommand):
    help = "Fetch Binance symbols, save to DB, and stream real-time prices using multiple WebSockets"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        self.stdout.write("📡 Fetching Binance symbols...")
        symbols = get_tradable_symbols()

        await self.save_assets(symbols)

        streams = [s["symbol"].lower() + "@trade" for s in symbols]

        self.stdout.write(f"✅ {len(streams)} symbols loaded")
        self.stdout.write(f"🔌 Starting {WORKER_COUNT} websocket connections...")

        tasks = []
        for i, chunk in enumerate(chunked(streams, MAX_STREAMS_PER_SOCKET)):
            if i >= WORKER_COUNT:
                break
            tasks.append(asyncio.create_task(self.websocket_worker(i + 1, chunk)))

        await asyncio.gather(*tasks)

    # ---------------------------
    # Save symbols to DB (SAFE)
    # ---------------------------

    @sync_to_async
    def save_assets(self, symbols):
        objs = [
            Stock(
                symbol=s["symbol"],
                name=f"{s['baseAsset']} / {s['quoteAsset']}",
                current_price=Decimal("0")
            )
            for s in symbols
        ]

        with transaction.atomic():
            Stock.objects.bulk_create(objs, ignore_conflicts=True)

        print(f"💾 Saved {len(objs)} assets")

    # ---------------------------
    # WebSocket Worker
    # ---------------------------

    async def websocket_worker(self, worker_id, streams):
        url = BINANCE_WS_BASE + "/".join(streams)
        self.stdout.write(f"🔗 Worker {worker_id} → {len(streams)} streams")

        buffer = {}
        last_flush = asyncio.get_event_loop().time()

        while True:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    async for msg in ws:
                        data = json.loads(msg)
                        payload = data.get("data")
                        if not payload:
                            continue

                        symbol = payload["s"]
                        price = Decimal(payload["p"])
                        buffer[symbol] = price

                        now = asyncio.get_event_loop().time()
                        if now - last_flush >= FLUSH_INTERVAL:
                            await self.flush_prices(buffer)
                            buffer.clear()
                            last_flush = now

            except Exception:
                logger.exception(f"⚠ Worker {worker_id} crashed — reconnecting in 3s...")
                await asyncio.sleep(3)

    # ---------------------------
    # Bulk DB Update (SAFE)
    # ---------------------------

    @sync_to_async
    def flush_prices(self, price_map):
        if not price_map:
            return

        assets = Stock.objects.filter(symbol__in=price_map.keys())
        for asset in assets:
            asset.current_price = price_map[asset.symbol]

        Stock.objects.bulk_update(assets, ["current_price"])
