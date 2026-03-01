import asyncio
import json
import logging
from decimal import Decimal
from itertools import islice

import websockets
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.utils import timezone

from stockmanagement.models import Stock


BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

MAX_STREAMS_PER_SOCKET = 300
FLUSH_INTERVAL = 0.5  # seconds

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


def to_decimal(value):
    try:
        return Decimal(value)
    except:
        return Decimal("0")


# ---------------------------
# Command
# ---------------------------

class Command(BaseCommand):
    help = "Stream real-time prices for existing Stock symbols"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    # ---------------------------
    # Main
    # ---------------------------

    async def main(self):

        self.stdout.write("📡 Loading symbols from database...")

        symbols = await self.get_symbols()

        if not symbols:
            self.stdout.write(self.style.ERROR("No symbols found in DB"))
            return

        streams = [symbol.lower() + "@ticker" for symbol in symbols]

        self.stdout.write(
            self.style.SUCCESS(f"✅ Loaded {len(streams)} symbols from DB")
        )

        tasks = []

        for worker_id, chunk in enumerate(
            chunked(streams, MAX_STREAMS_PER_SOCKET), start=1
        ):
            tasks.append(
                asyncio.create_task(
                    self.websocket_worker(worker_id, chunk)
                )
            )

        await asyncio.gather(*tasks)

    # ---------------------------
    # Get symbols from DB
    # ---------------------------

    @sync_to_async
    def get_symbols(self):
        return list(
            Stock.objects.values_list("symbol", flat=True)
        )

    # ---------------------------
    # WebSocket Worker
    # ---------------------------

    async def websocket_worker(self, worker_id, streams):

        url = BINANCE_WS_BASE + "/".join(streams)

        self.stdout.write(
            f"🔌 Worker {worker_id} started ({len(streams)} streams)"
        )

        buffer = {}
        last_flush = asyncio.get_event_loop().time()

        while True:

            try:

                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                    max_size=None
                ) as ws:

                    async for msg in ws:

                        data = json.loads(msg)
                        payload = data.get("data")

                        if not payload:
                            continue

                        symbol = payload["s"]

                        buffer[symbol] = {

                            "current_price": to_decimal(payload["c"]),
                            "open_price": to_decimal(payload["o"]),
                            "high_price": to_decimal(payload["h"]),
                            "low_price": to_decimal(payload["l"]),

                            "bid_price": to_decimal(payload["b"]),
                            "ask_price": to_decimal(payload["a"]),

                            "price_change": to_decimal(payload["p"]),
                            "percentage_change": to_decimal(payload["P"]),

                            "quote_volume_24h": to_decimal(payload["q"]),

                            "last_updated": timezone.now(),
                        }

                        now = asyncio.get_event_loop().time()

                        if now - last_flush >= FLUSH_INTERVAL:

                            await self.flush_prices(buffer)

                            buffer.clear()
                            last_flush = now

            except Exception as e:

                logger.exception(
                    f"Worker {worker_id} crashed: {e}"
                )

                await asyncio.sleep(3)

    # ---------------------------
    # Flush to DB
    # ---------------------------

    @sync_to_async
    def flush_prices(self, price_map):

        if not price_map:
            return

        symbols = list(price_map.keys())

        stocks = list(
            Stock.objects.filter(symbol__in=symbols)
        )

        for stock in stocks:

            data = price_map.get(stock.symbol)

            if not data:
                continue

            stock.current_price = data["current_price"]
            stock.open_price = data["open_price"]
            stock.high_price = data["high_price"]
            stock.low_price = data["low_price"]

            stock.bid_price = data["bid_price"]
            stock.ask_price = data["ask_price"]

            stock.price_change = data["price_change"]
            stock.percentage_change = data["percentage_change"]

            stock.quote_volume_24h = data["quote_volume_24h"]

            stock.last_updated = data["last_updated"]

        Stock.objects.bulk_update(
            stocks,
            [
                "current_price",
                "open_price",
                "high_price",
                "low_price",
                "bid_price",
                "ask_price",
                "price_change",
                "percentage_change",
                "quote_volume_24h",
                "last_updated",
            ],
            batch_size=500
        )