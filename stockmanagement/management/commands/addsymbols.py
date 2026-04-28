import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from stockmanagement.models import Stock


EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"


def to_decimal(value, default="0"):
    """Safely convert value to Decimal"""
    try:
        return Decimal(str(value))
    except:
        return Decimal(default)


class Command(BaseCommand):
    help = "Fetch and add/update symbols from Binance"

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.SUCCESS("Fetching symbols from Binance..."))

        # Fetch exchange info
        exchange_response = requests.get(EXCHANGE_INFO_URL, timeout=30)
        exchange_data = exchange_response.json()

        symbols_info = {
            s["symbol"]: {
                "base": s["baseAsset"],
                "quote": s["quoteAsset"]
            }
            for s in exchange_data["symbols"]
            if s["status"] == "TRADING"
        }

        # Fetch ticker data
        ticker_response = requests.get(TICKER_24HR_URL, timeout=30)
        ticker_data = ticker_response.json()

        ticker_map = {
            t["symbol"]: t
            for t in ticker_data
        }

        # Fetch existing symbols from DB
        existing_symbols = set(
            Stock.objects.values_list("symbol", flat=True)
        )

        new_objects = []
        update_objects = []

        now = timezone.now()

        for symbol, info in symbols_info.items():

            ticker = ticker_map.get(symbol)

            if not ticker:
                continue

            obj_data = {
                "symbol": symbol,
                "name": symbol,
                "base_asset": info["base"],
                "quote_asset": info["quote"],

                "open_price": to_decimal(ticker["openPrice"]),
                "high_price": to_decimal(ticker["highPrice"]),
                "low_price": to_decimal(ticker["lowPrice"]),
                "close_price": to_decimal(ticker["lastPrice"]),
                "current_price": to_decimal(ticker["lastPrice"]),

                "bid_price": to_decimal(ticker["bidPrice"]),
                "ask_price": to_decimal(ticker["askPrice"]),

                "high_24h": to_decimal(ticker["highPrice"]),
                "low_24h": to_decimal(ticker["lowPrice"]),
                "quote_volume_24h": to_decimal(ticker["quoteVolume"]),

                "price_change": to_decimal(ticker["priceChange"]),
                "percentage_change": to_decimal(ticker["priceChangePercent"]),

                "last_updated": now
            }

            if symbol in existing_symbols:

                update_objects.append(
                    Stock(**obj_data)
                )

            else:

                new_objects.append(
                    Stock(**obj_data)
                )

        self.stdout.write(f"New symbols: {len(new_objects)}")
        self.stdout.write(f"Updating symbols: {len(update_objects)}")

        with transaction.atomic():

            # Bulk create new
            if new_objects:
                Stock.objects.bulk_create(
                    new_objects,
                    batch_size=500
                )

            # Bulk update existing
            if update_objects:

                Stock.objects.bulk_update(
                    update_objects,
                    fields=[
                        "open_price",
                        "high_price",
                        "low_price",
                        "close_price",
                        "current_price",
                        "bid_price",
                        "ask_price",
                        "high_24h",
                        "low_24h",
                        "quote_volume_24h",
                        "price_change",
                        "percentage_change",
                        "last_updated",
                    ],
                    batch_size=500
                )

        self.stdout.write(
            self.style.SUCCESS("Symbols synced successfully.")
        )