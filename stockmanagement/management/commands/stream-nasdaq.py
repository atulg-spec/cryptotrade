import json
import websocket
import threading
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from stockmanagement.models import Stock
from dashboard.models import APISettings


class Command(BaseCommand):
    help = "High performance NASDAQ streaming"

    WS_URL = "wss://stream.data.alpaca.markets/v2/iex"

    BATCH_UPDATE_INTERVAL = 1
    SYMBOL_REFRESH_INTERVAL = 5  # check DB every 5 cycles

    def handle(self, *args, **kwargs):

        api = APISettings.objects.first()

        if not api:
            self.stdout.write(self.style.ERROR("API settings not found"))
            return

        stocks = Stock.objects.filter(exchange="NASDAQ")

        if not stocks.exists():
            self.stdout.write(self.style.ERROR("No NASDAQ stocks found"))
            return

        self.stdout.write(f"Streaming {stocks.count()} NASDAQ symbols")

        # in memory cache
        self.stock_cache = {s.symbol: s for s in stocks}
        self.symbols = set(self.stock_cache.keys())

        self.updated_symbols = set()

        self.update_cycle = 0

        self.ws = None

        threading.Thread(target=self.bulk_updater, daemon=True).start()

        self.connect_ws(api)

    # ---------------------
    # WEBSOCKET CONNECTION
    # ---------------------

    def connect_ws(self, api):

        def on_open(ws):

            self.ws = ws

            print("Connected to Alpaca")

            ws.send(json.dumps({
                "action": "auth",
                "key": api.api_key,
                "secret": api.secret_key
            }))

            ws.send(json.dumps({
                "action": "subscribe",
                "trades": list(self.symbols),
                "quotes": list(self.symbols)
            }))

            print("Subscribed to trades + quotes")

        def on_message(ws, message):

            data = json.loads(message)

            for msg in data:

                msg_type = msg.get("T")

                if msg_type == "t":

                    symbol = msg["S"]
                    price = Decimal(str(msg["p"]))
                    size = Decimal(str(msg["s"]))

                    stock = self.stock_cache.get(symbol)

                    if not stock:
                        continue

                    stock.current_price = price
                    stock.quote_volume_24h += size

                    if stock.high_price == 0 or price > stock.high_price:
                        stock.high_price = price

                    if stock.low_price == 0 or price < stock.low_price:
                        stock.low_price = price

                    stock.price_change = price - stock.open_price

                    if stock.open_price > 0:
                        stock.percentage_change = (
                            (price - stock.open_price) / stock.open_price
                        ) * 100

                    stock.last_updated = timezone.now()

                    self.updated_symbols.add(symbol)

                elif msg_type == "q":

                    symbol = msg["S"]

                    stock = self.stock_cache.get(symbol)

                    if not stock:
                        continue

                    stock.bid_price = Decimal(str(msg["bp"]))
                    stock.ask_price = Decimal(str(msg["ap"]))

                    self.updated_symbols.add(symbol)

        def on_error(ws, error):
            print("WebSocket error:", error)

        def on_close(ws, close_status_code, close_msg):
            print("WebSocket closed, reconnecting in 5s...")
            time.sleep(5)
            self.connect_ws(api)

        ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        ws.run_forever()

    # --------------------------
    # CHECK NEW SYMBOLS
    # --------------------------

    def check_new_symbols(self):

        stocks = Stock.objects.filter(exchange="NASDAQ")

        new_symbols = []

        for s in stocks:

            if s.symbol not in self.symbols:
                self.symbols.add(s.symbol)
                self.stock_cache[s.symbol] = s
                new_symbols.append(s.symbol)

        if new_symbols and self.ws:

            print(f"New symbols detected: {new_symbols}")

            self.ws.send(json.dumps({
                "action": "subscribe",
                "trades": new_symbols,
                "quotes": new_symbols
            }))

            print("Subscribed to new symbols")

    # --------------------------
    # BULK DATABASE UPDATER
    # --------------------------

    def bulk_updater(self):

        while True:

            time.sleep(self.BATCH_UPDATE_INTERVAL)

            if self.updated_symbols:

                stocks_to_update = [
                    self.stock_cache[s]
                    for s in self.updated_symbols
                ]

                Stock.objects.bulk_update(
                    stocks_to_update,
                    [
                        "current_price",
                        "quote_volume_24h",
                        "high_price",
                        "low_price",
                        "bid_price",
                        "ask_price",
                        "price_change",
                        "percentage_change",
                        "last_updated"
                    ]
                )

                self.updated_symbols.clear()

            # increment cycle
            self.update_cycle += 1

            # check for new symbols
            if self.update_cycle % self.SYMBOL_REFRESH_INTERVAL == 0:
                self.check_new_symbols()