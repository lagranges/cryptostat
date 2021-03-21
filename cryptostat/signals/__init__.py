#! /usr/bin/env python3


class Signal(object):

    PERIOD_UNIT = 15  # minutes

    def __init__(
            self, symbol, last_open_time_str,
            period, minimum_percentage, percentage
        ):
        self.symbol = symbol
        self.period = period
        self.minimum_percentage = minimum_percentage
        self.percentage = percentage
        self.last_open_time_str = last_open_time_str

    @property
    def since(self):
        return self.PERIOD_UNIT*self.period

    @property
    def level(self):
        return int(self.percentage-self.minimum_percentage)


class PumpSingal(Signal):

    def __repr__(self):
        return (
            f"[{self.symbol}][SELL][{self.level}]"
            f"[{self.last_open_time_str}] "
            f" pumped {self.percentage}% since {self.since}"
            f" minutes"
        )


class DumpSingal(Signal):

    def __repr__(self):
        return (
            f"[{self.symbol}][BUY][{self.level}]"
            f"[{self.last_open_time_str}] "
            f" dumped {self.percentage} % since {self.since}"
            f" minutes"
        )
