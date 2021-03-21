#! /usr/bin/env python3
import os
import time
import datetime
from .data_provider import BinaceClient
from .signals import DumpSingal, PumpSingal
from .notifier import send_message
from .tools import now
import traceback


client = BinaceClient()
EXCLUDED_SYMBOLS = ["DOTECOUSDT", "DEFIUSDT"]
LAST_TIME_SENT = {}
HEARTBEAT = 0.5  # minute
DELAY_TO_SEND_MESSAGE = 1  # minute
PUMPING_PERIODS = [2,3,4,5]
MINIMUM_PUMPING = 5
DUMPING_PERIODS = [1,2,3,4]
MINIMUM_DUMPING = 3
DEFAULT_PARAM = {
        "pumping": [
            {"period": 5, "minimum_percentage": 5},
            {"period": 4, "minimum_percentage": 7},
            {"period": 3, "minimum_percentage": 8},
            {"period": 2, "minimum_percentage": 9},
            {"period": 1, "minimum_percentage": 10},
            ],
        "dumping": [
            {"period": 1, "minimum_percentage": 3},
            {"period": 2, "minimum_percentage": 4},
            {"period": 3, "minimum_percentage": 5},
            {"period": 4, "minimum_percentage": 6},
            ]
}
DEBUG_PARAM = {
        "pumping": [
            {"period": 1, "minimum_percentage": 0}
            ],
        "dumping": [
            {"period": 1, "minimum_percentage": 0}
            ],
        }
DEBUG_MODE = True


def get_signal_params(symbols, since="20 days ago UTC"):
    signal_params = {}
    for symbol in symbols:
        params = {}
        if DEBUG_MODE:
            signal_params[symbol] = DEBUG_PARAM
            continue
        try:
            data = client.get_klines(symbol, "15m", since)
            params["pumping"] = []
            params["dumping"] = []
            for period in PUMPING_PERIODS:
                pumping_medium = data.pumping_percentage_mean(
                    period=period, minimum_percentage=MINIMUM_PUMPING
                )
                if pumping_medium:
                    params["pumping"].append(
                            {
                                "period": period,
                                "minimum_percentage": pumping_medium
                                }
                            )
            for period in DUMPING_PERIODS:
                dumping_medium = data.dumping_percentage_mean(
                    period=period, minimum_percentage=MINIMUM_PUMPING
                )
                if dumping_medium:
                    params["dumping"].append(
                            {
                                "period": period,
                                "minimum_percentage": dumping_medium
                                }
                            )
        except Exception:
            import traceback;traceback.print_exc()
            print(f"Failed to get param for {symbol}")
        finally:
            signal_params[symbol] = params
    return signal_params


def get_signals(symbol, params):
    data = client.get_klines(symbol, "15m", "10 days ago UTC")
    signals = []
    for param in params["pumping"]:
        signal_data = data.pumping_percentage(**param)
        for time, percentage in signal_data.items():
            signal = PumpSingal(
                symbol, time, param["period"],
                param["minimum_percentage"], percentage
            )
            signals.append(signal)
    for param in params["dumping"]:
        signal_data = data.dumping_percentage(**param)
        for time, percentage in signal_data.items():
            signal = PumpSingal(
                symbol, time, param["period"],
                param["minimum_percentage"], percentage
            )
            signals.append(signal)
    return signals


def get_live_signals(symbol, params):
    data = client.get_klines(symbol, "15m", "2 hours ago UTC")
    signals = []
    now_str = now()
    for param in params["pumping"]:
        percentage = data.live_pumping_percentage(**param)
        if percentage > 0:
            signal = PumpSingal(
                symbol, now_str, param["period"],
                param["minimum_percentage"], percentage
            )
            signals.append(signal)
    for param in params["dumping"]:
        percentage = data.live_dumping_percentage(**param)
        if percentage > 0:
            signal = DumpSingal(
                symbol, now_str, param["period"],
                param["minimum_percentage"], percentage
            )
            signals.append(signal)
    return signals


def main():
    send_message(f"[CryptoStat] Start at {now()}\n")
    send_message(f"[CryptoStat][{now()}] Loading params\n")
    perp_symbols = sorted(list(
        set(client.get_all_perp_symbols()) | set(EXCLUDED_SYMBOLS)
    ))
    if DEBUG_MODE:
        perp_symbols = perp_symbols[:3]
    signal_params = get_signal_params(perp_symbols)
    print(signal_params)
    send_message(f"[CryptoStat][{now()}] Loaded params")
    while True:
        print("Tick !")
        message = ""
        header = ""
        for symbol in perp_symbols:
            print(f"[{now()}] get signals for {symbol}")
            try:
                params = signal_params.get(symbol)
                if not params:
                    print(f"[now()] params not found for {symbol}")
                    continue
                signals = get_live_signals(symbol, params)
                print(signals)
                last_time_sent = time.time() - LAST_TIME_SENT.get(symbol, 0)
                if last_time_sent < DELAY_TO_SEND_MESSAGE * 60:
                    print(f"[{now()}] Skip messages for {symbol}")
                    continue
                if signals:
                    header += f"{symbol} "
                    message += "\n".join(map(str, signals))
                    message += "\n"
                    LAST_TIME_SENT[symbol] = time.time()
            except Exception:
                message += "Failed to get signals for {symbol}\n"
                message += traceback.format_exc()
        if message:
            message = header + "\n" +  message
            print(f"[{now()}] {message}")
            send_message(message)
        time.sleep(HEARTBEAT*60)

if __name__ == "__main__":
    main()
