#! /usr/bin/env python3
import os
import json
import numpy
import requests
import datetime
from typing import NamedTuple, List, Dict
from binance.client import Client

API_KEY = os.environ["BINANCE_API_KEY"]
API_SECRET = os.environ["BINANCE_API_SECRET"]
COIN_MARKET_CAP_URL = "https://pro-api.coinmarketcap.com"


class BinanceKlineData(NamedTuple):
    open_time: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    close_time: float
    quote_asset_volume: float
    number_of_trades: float
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float
    ignore: float

    @property
    def open_time_str(self):
        d = datetime.datetime.fromtimestamp(
                self.open_time/1000
        )
        return d.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def is_green(self):
        return (
            self.close_price - self.open_price
        ) > 0

    @property
    def percentage(self):
        return (
            ((self.close_price - self.open_price) * 100.0)/ self.open_price
        )


class Indicator(object):

    def __init__(self, candles: List[BinanceKlineData]):
        self.candles = candles

    @property
    def dumping_percentage(self):
        if any([d.is_green for d in self.candles]):
            return 0
        high = self.candles[0].high_price
        low = self.candles[-1].low_price
        return round((high - low) / high * 100, 2)

    @property
    def live_dumping_percentage(self):
        if any([d.is_green for d in self.candles]):
            return 0
        high = self.candles[0].high_price
        close = self.candles[-1].close_price
        return round((high - close) / close * 100, 2)

    @property
    def pumping_percentage(self):
        if not all([d.is_green for d in self.candles]):
            return 0
        low = self.candles[0].low_price
        high = self.candles[-1].high_price
        return round((high - low) / low * 100, 2)

    @property
    def live_pumping_percentage(self):
        if not all([d.is_green for d in self.candles]):
            return 0
        low = self.candles[0].low_price
        close = self.candles[-1].close_price
        return round((close - low) / close * 100, 2)


class BinanceKlinesData(object):

    def __init__(self, data: List[BinanceKlineData]):
        self.data = data

    def sorted_by(self, by="percentage", filter_func=lambda x: True):
        return sorted(filter(self.data, filter_func), lambda d: getattr(d, by))

    def max_by(self, by="percentage", filter_func=lambda x:True):
        return max(
            filter(filter_func, self.data),key=lambda d: getattr(d, by)
        )

    def dumping_percentage(self, period=3, minimum_percentage=0):
        length = len(self.data)
        res = {}
        if length < period:
            return res
        for i in range(period-1, length):
            candles = self.data[i-period+1:i+1]
            dp = Indicator(candles).dumping_percentage
            if dp > minimum_percentage:
                res[self.data[i].open_time_str] = Indicator(candles).dumping_percentage
        return res

    def pumping_percentage(self, period=3, minimum_percentage=0):
        length = len(self.data)
        res = {}
        if length < period:
            return res
        for i in range(period-1, length):
            candles = self.data[i-period+1:i+1]
            pp = Indicator(candles).pumping_percentage
            if pp >= minimum_percentage:
                res[self.data[i].open_time_str] = pp
        return res

    def live_pumping_percentage(self, period=3, minimum_percentage=0):
        length = len(self.data)
        candles = self.data[length-period:]
        pp = Indicator(candles).live_pumping_percentage
        if pp >= minimum_percentage:
            return pp
        else:
            return 0

    def pumping_percentage_mean(self, period=3, minimum_percentage=0):
        pp = self.pumping_percentage(period, minimum_percentage)
        res = numpy.mean(list(pp.values()))
        if numpy.isnan(res):
            return None
        return res

    def dumping_percentage_mean(self, period=3, minimum_percentage=0):
        pp = self.dumping_percentage(period, minimum_percentage)
        res = numpy.mean(list(pp.values()))
        if numpy.isnan(res):
            return None
        return res

    def live_dumping_percentage(self, period=3, minimum_percentage=0):
        length = len(self.data)
        candles = self.data[length-period:]
        pp = Indicator(candles).live_dumping_percentage
        if pp >= minimum_percentage:
            return pp
        else:
            return 0

#     def rsi(self, period=10):
#         length = len(self.data)
#         for i in range(0, length-period):
#             changes_bar_to_bar = [
#                     d.close_price - d_prev.close_price for d, d_prev in zip(
#                         d[i:period+i], d[i-1:period+i-1]
#                         )
#                     ]
#             U = [c in changes_bar_to_bar if c > 0]
#             D = [-c in changes_bar_to_bar if c < 0]
#             AvgU = sum(U)/period


class BinanceKlinesGroup(object):

    def __init__(self, data: Dict[str, BinanceKlinesData]):
        self.data = data


class BinaceClient(object):

    TESTNET_URL = "https://testnet.binancefuture.com"
    PERIOD_MAPPNG = {
        "5m": Client.KLINE_INTERVAL_15MINUTE,
    }

    def __init__(self, api_key=API_KEY, api_secret=API_SECRET):
        self._api_key = api_key
        self._api_secret = api_secret
        self.client = Client(self._api_key, self._api_secret)

    def get_all_perp_symbols(self):
        url = f"{self.TESTNET_URL}/fapi/v1/exchangeInfo"
        symbol_infos = requests.get(url).json()
        symbol_infos = symbol_infos["symbols"]
        perputal_infos = [
            e for e in symbol_infos if e["contractType"] == "PERPETUAL"
        ]
        perputal_symbols = [e["symbol"] for e in perputal_infos]
        return perputal_symbols

    def get_all_symbols(self, base="USDT"):
        return [
            ticker["symbol"] for ticker in self.client.get_all_tickers() if (
                ticker["symbol"].endswith(base)
                )
            ]

    def get_klines(self, symbol, period, since):
        klines = self.client.get_historical_klines(
            symbol, period, since
        )
        data = [
            BinanceKlineData(*list(map(float,kline))) for kline in klines
        ]
        return BinanceKlinesData(data)


def get_all_market_caps():
    url = f"{COIN_MARKET_CAP_URL}/v1/cryptocurrency/listings/latest"
    headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': '3247c449-72ea-404c-bcd2-88e793b06e24',
    }
    try:
        res = {}
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)["data"]
        for d in data:
            symbol = d["symbol"]
            market_cap = d["quote"]["USD"]["market_cap"]
            binance_symbol = f"{symbol}USDT"
            res[binance_symbol] = market_cap
    except Exception:
        import traceback;traceback.print_exc()
        res = {}
    return res

