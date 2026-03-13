"""
Django Management Command: stream_forex_prices
==============================================

Streams Forex prices using Frankfurter API.

Features
--------
✔ Reads symbols from Stock model (exchange="FOREX")
✔ Polls prices every second
✔ High-performance bulk database updates
✔ Automatically detects new symbols added to DB
✔ Thread-safe update buffer

API: https://www.frankfurter.app

Usage
-----
python manage.py stream_forex_prices
python manage.py stream_forex_prices --interval 2
"""

import requests
import threading
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from stockmanagement.models import Stock

API_BASE = "https://api.frankfurter.app/latest"

BATCH_UPDATE_INTERVAL = 1
SYMBOL_REFRESH_INTERVAL = 10


# ─────────────────────────────────────────────
# Thread Safe Price Buffer
# ─────────────────────────────────────────────

class PriceBuffer:

    def __init__(self):
        self.lock = threading.Lock()
        self.buffer = {}

    def update(self, symbol, price):

        with self.lock:
            self.buffer[symbol] = price

    def flush(self):

        with self.lock:
            snap = dict(self.buffer)
            self.buffer.clear()
            return snap


# ─────────────────────────────────────────────
# Fetch Forex Rates
# ─────────────────────────────────────────────

def parse_symbol(symbol):

    symbol = symbol.upper()

    if len(symbol) != 6:
        return None, None

    return symbol[:3], symbol[3:]


def fetch_rates(symbols):

    bases = {}
    result = {}

    for sym in symbols:

        base, quote = parse_symbol(sym)

        if not base:
            continue

        bases.setdefault(base, []).append((sym, quote))

    for base, pairs in bases.items():

        quotes = [q for _, q in pairs if q != base]

        if not quotes:
            continue

        try:

            r = requests.get(
                API_BASE,
                params={"from": base, "to": ",".join(quotes)},
                timeout=5,
            )

            data = r.json().get("rates", {})

            for sym, quote in pairs:

                price = data.get(quote)

                if price:
                    result[sym] = price

        except Exception as e:
            print("Fetch error:", e)

    return result


# ─────────────────────────────────────────────
# Bulk Database Updater
# ─────────────────────────────────────────────

class DBUpdater(threading.Thread):

    def __init__(self, buffer, stop_event):

        super().__init__(daemon=True)

        self.buffer = buffer
        self.stop_event = stop_event
        self.total_updates = 0

    def run(self):

        while not self.stop_event.is_set():

            time.sleep(BATCH_UPDATE_INTERVAL)

            snap = self.buffer.flush()

            if not snap:
                continue

            stocks = {
                s.symbol: s
                for s in Stock.objects.filter(symbol__in=snap.keys())
            }

            updated = []

            for sym, price in snap.items():

                stock = stocks.get(sym)

                if not stock:
                    continue

                price = Decimal(str(price))

                stock.current_price = price

                if stock.open_price and stock.open_price > 0:

                    stock.price_change = price - stock.open_price

                    stock.percentage_change = (
                        stock.price_change / stock.open_price
                    ) * 100

                stock.last_updated = timezone.now()

                updated.append(stock)

            if updated:

                with transaction.atomic():

                    Stock.objects.bulk_update(
                        updated,
                        [
                            "current_price",
                            "price_change",
                            "percentage_change",
                            "last_updated",
                        ],
                    )

                self.total_updates += len(updated)


# ─────────────────────────────────────────────
# Symbol Monitor Worker
# ─────────────────────────────────────────────

class SymbolMonitor(threading.Thread):

    def __init__(self, command):

        super().__init__(daemon=True)

        self.command = command

    def run(self):

        while not self.command.stop_event.is_set():

            time.sleep(SYMBOL_REFRESH_INTERVAL)

            stocks = Stock.objects.filter(exchange__iexact="FOREX")

            new_symbols = []

            for s in stocks:

                if s.symbol not in self.command.symbols:

                    self.command.symbols.add(s.symbol)

                    new_symbols.append(s.symbol)

            if new_symbols:

                print("New FOREX symbols detected:", new_symbols)


# ─────────────────────────────────────────────
# Management Command
# ─────────────────────────────────────────────

class Command(BaseCommand):

    help = "Stream forex prices from Frankfurter API"

    def add_arguments(self, parser):

        parser.add_argument(
            "--interval",
            type=float,
            default=1,
            help="Polling interval seconds",
        )

    def get_symbols(self):

        symbols = list(
            Stock.objects.filter(exchange__iexact="FOREX")
            .values_list("symbol", flat=True)
        )

        if not symbols:
            raise Exception("No FOREX symbols found")

        return symbols

    def handle(self, *args, **options):

        interval = options["interval"]

        self.stop_event = threading.Event()

        symbols = self.get_symbols()

        self.symbols = set(symbols)

        print("\nForex streamer started")
        print("Streaming:", ", ".join(symbols))

        buffer = PriceBuffer()

        updater = DBUpdater(buffer, self.stop_event)

        updater.start()

        monitor = SymbolMonitor(self)

        monitor.start()

        try:

            while True:

                rates = fetch_rates(list(self.symbols))

                for sym, price in rates.items():

                    buffer.update(sym, price)

                time.sleep(interval)

        except KeyboardInterrupt:

            print("Stopping streamer")

            self.stop_event.set()

        print("Total DB updates:", updater.total_updates)
