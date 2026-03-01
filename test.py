import requests
import pandas as pd
from datetime import datetime

# Binance API endpoints
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

def get_all_symbols():
    """Fetch all trading symbols from Binance"""
    response = requests.get(EXCHANGE_INFO_URL)
    data = response.json()

    symbols_info = {}

    for symbol in data['symbols']:
        if symbol['status'] == 'TRADING':
            symbols_info[symbol['symbol']] = {
                "baseAsset": symbol['baseAsset'],
                "quoteAsset": symbol['quoteAsset']
            }

    return symbols_info


def get_live_market_data():
    """Fetch live ticker data for all symbols"""
    response = requests.get(TICKER_24HR_URL)
    return response.json()
