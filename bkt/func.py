from bkt.constant import Exchange,Interval
from typing import Tuple,Callable,Dict
from bkt.base import Bar,Tick
import numpy as np
import talib
from functools import lru_cache
from datetime import datetime
from bkt.database import database_manager


class BarGenerator:
    """
    1. generating 1 minute bar data from tick data
    2. generateing x minute bar/x hour bar data from 1 minute data
    """

    def __init__(self,
                 on_bar:Callable,
                 window:int=0,
                 on_window_bar:Callable=None,
                 interval: Interval=Interval.MINUTE):
        self.bar: Bar = None
        self.on_bar: Callable = on_bar

        self.interval: Interval = interval
        self.interval_count: int = 0

        self.window: int = window
        self.window_bar: Bar = None
        self.on_window_bar: Callable = on_window_bar

        self.last_tick: Tick = None
        self.last_bar: Bar = None

    def update_tick(self,tick:Tick):
        new_minute = False

        if not tick.last_price:
            return

        if not self.bar:
            new_minute = True
        elif self.bar.datetime.minute != tick.datetime.minute:
            self.bar.datetime = self.bar.datetime.replace(second=0,microsecond=0)
            self.on_bar(self.bar)

            new_minute = True

        if new_minute:
            self.bar = Bar(time=tick.datetime,
                           vt_symbol=tick.vt_symbol,
                           open=tick.last_price,
                           high=tick.last_price,
                           low=tick.last_price,
                           close=tick.last_price,
                           open_interest=tick.open_interest,
                           multiplier=tick.multiplier)

        else:
            self.bar.high = max(self.bar.high,tick.last_price)
            self.bar.low = min(self.bar.low,tick.last_price)
            self.bar.close = tick.last_price
            self.bar.open_interest = tick.open_interest
            self.bar.datetime = tick.datetime

        if self.last_tick:
            volume_change = tick.last_volume - self.last_tick.last_volume
            self.bar.volume += max(volume_change,0)

        self.last_tick = tick

    def update_bar(self,bar:Bar):
        if not self.window_bar:
            if self.interval == Interval.MINUTE:
                dt = bar.datetime.replace(second=0,microsecond=0)
            else:
                dt = bar.datetime.replace(minute=0,second=0,microsecond=0)

            self.window_bar = Bar(time=dt,
                                  vt_symbol=bar.vt_symbol,
                                  open=bar.open,
                                  high=bar.high,
                                  low=bar.low,
                                  multiplier=bar.multiplier
                                  )
        else:
            self.window_bar.high = max(self.window_bar.high,bar.high)
            self.window_bar.low = min(self.window_bar.low,bar.low)

        self.window_bar.datetime = bar.datetime
        self.window_bar.close = bar.close
        self.window_bar.volume += int(bar.volume)
        self.window_bar.open_interest = bar.open_interest

        finished = False

        if self.interval == Interval.MINUTE:
            # x-minute bar
            if not bar.datetime.minute % self.window:
                finished = True
        elif self.interval == Interval.HOUR:
            if self.last_bar and bar.datetime.hour != self.last_bar.datetime.hour:
                # 1-hour bar
                if self.window == 1:
                    finished = True
                # x-hour bar
                else:
                    self.interval_count += 1

                    if not self.interval_count % self.window:
                        finished = True
                        self.interval_count = 0

        if finished:
            self.on_window_bar(self.window_bar)
            self.window_bar = None

        # Cache last bar object
        self.last_bar = bar


class BarManager:
    """
    1. time series container of bar data
    2. calculating technical indicator value
    """

    def __init__(self,size: int=100):
        self.count: int = 0
        self.size: int = size
        self.inited: bool = False

        self.open_array: np.ndarray = np.zeros(size)
        self.high_array: np.ndarray = np.zeros(size)
        self.low_array: np.ndarray = np.zeros(size)
        self.close_array: np.ndarray = np.zeros(size)
        self.volume_array: np.ndarray = np.zeros(size)
        self.open_interest_array: np.ndarray = np.zeros(size)

    def update_bar(self,bar:Bar):
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited =True

        self.open_array[:-1] = self.open_array[1:]
        self.high_array[:-1] = self.high_array[1:]
        self.low_array[:-1] = self.low_array[1:]
        self.close_array[:-1] = self.close_array[1:]
        self.volume_array[:-1] = self.volume_array[1:]
        self.open_interest_array[:-1] = self.open_interest_array[1:]

        self.open_array[-1] = bar.open
        self.high_array[-1] = bar.high
        self.low_array[-1] = bar.low
        self.close_array[-1] = bar.close
        self.volume_array[-1] = bar.volume
        self.open_interest_array[-1] = bar.open_interest

    @property
    def open(self):
        return self.open_array

    @property
    def high(self):
        return self.high_array

    @property
    def low(self):
        return self.low_array

    @property
    def close(self):
        return self.close_array

    @property
    def volume(self):
        return self.volume_array

    @property
    def open_interest(self):
        return self.open_interest_array

    def sma(self, n: int, array: bool = False):
        """
        Simple moving average.
        """
        result = talib.SMA(self.close, n)
        if array:
            return result
        return result[-1]

    def ema(self, n: int, array: bool = False):
        """
        Exponential moving average.
        """
        result = talib.EMA(self.close, n)
        if array:
            return result
        return result[-1]

    def kama(self, n: int, array: bool = False):
        """
        KAMA.
        """
        result = talib.KAMA(self.close, n)
        if array:
            return result
        return result[-1]

    def wma(self, n: int, array: bool = False):
        """
        WMA.
        """
        result = talib.WMA(self.close, n)
        if array:
            return result
        return result[-1]

    def apo(self, n: int, array: bool = False):
        """
        APO.
        """
        result = talib.APO(self.close, n)
        if array:
            return result
        return result[-1]

    def cmo(self, n: int, array: bool = False):
        """
        CMO.
        """
        result = talib.CMO(self.close, n)
        if array:
            return result
        return result[-1]

    def mom(self, n: int, array: bool = False):
        """
        MOM.
        """
        result = talib.MOM(self.close, n)
        if array:
            return result
        return result[-1]

    def ppo(self, n: int, array: bool = False):
        """
        PPO.
        """
        result = talib.PPO(self.close, n)
        if array:
            return result
        return result[-1]

    def roc(self, n: int, array: bool = False):
        """
        ROC.
        """
        result = talib.ROC(self.close, n)
        if array:
            return result
        return result[-1]

    def rocr(self, n: int, array: bool = False):
        """
        ROCR.
        """
        result = talib.ROCR(self.close, n)
        if array:
            return result
        return result[-1]

    def rocp(self, n: int, array: bool = False):
        """
        ROCP.
        """
        result = talib.ROCP(self.close, n)
        if array:
            return result
        return result[-1]

    def rocr_100(self, n: int, array: bool = False):
        """
        ROCR100.
        """
        result = talib.ROCR100(self.close, n)
        if array:
            return result
        return result[-1]

    def trix(self, n: int, array: bool = False):
        """
        TRIX.
        """
        result = talib.TRIX(self.close, n)
        if array:
            return result
        return result[-1]

    def std(self, n: int, array: bool = False):
        """
        Standard deviation.
        """
        result = talib.STDDEV(self.close, n)
        if array:
            return result
        return result[-1]

    def obv(self, n: int, array: bool = False):
        """
        OBV.
        """
        result = talib.OBV(self.close, self.volume)
        if array:
            return result
        return result[-1]

    def cci(self, n: int, array: bool = False):
        """
        Commodity Channel Index (CCI).
        """
        result = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def atr(self, n: int, array: bool = False):
        """
        Average True Range (ATR).
        """
        result = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def natr(self, n: int, array: bool = False):
        """
        NATR.
        """
        result = talib.NATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def rsi(self, n: int, array: bool = False):
        """
        Relative Strenght Index (RSI).
        """
        result = talib.RSI(self.close, n)
        if array:
            return result
        return result[-1]

    def macd(
        self,
        fast_period: int,
        slow_period: int,
        signal_period: int,
        array: bool = False
    ):
        """
        MACD.
        """
        macd, signal, hist = talib.MACD(
            self.close, fast_period, slow_period, signal_period
        )
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]

    def adx(self, n: int, array: bool = False):
        """
        ADX.
        """
        result = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def adxr(self, n: int, array: bool = False):
        """
        ADXR.
        """
        result = talib.ADXR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def dx(self, n: int, array: bool = False):
        """
        DX.
        """
        result = talib.DX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def minus_di(self, n: int, array: bool = False):
        """
        MINUS_DI.
        """
        result = talib.MINUS_DI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def plus_di(self, n: int, array: bool = False):
        """
        PLUS_DI.
        """
        result = talib.PLUS_DI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def willr(self, n: int, array: bool = False):
        """
        WILLR.
        """
        result = talib.WILLR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    def ultosc(self, array: bool = False):
        """
        Ultimate Oscillator.
        """
        result = talib.ULTOSC(self.high, self.low, self.close)
        if array:
            return result
        return result[-1]

    def trange(self, array: bool = False):
        """
        TRANGE.
        """
        result = talib.TRANGE(self.high, self.low, self.close)
        if array:
            return result
        return result[-1]

    def boll(
        self,
        n: int,
        dev: float,
        array: bool = False
    ):
        """
        Bollinger Channel.
        """
        mid = self.sma(n, array)
        std = self.std(n, array)

        up = mid + std * dev
        down = mid - std * dev

        return up,mid, down

    def keltner(
        self,
        n: int,
        dev: float,
        array: bool = False
    ):
        """
        Keltner Channel.
        """
        mid = self.sma(n, array)
        atr = self.atr(n, array)

        up = mid + atr * dev
        down = mid - atr * dev

        return up, down

    def donchian(
        self, n: int, array: bool = False
    ):
        """
        Donchian Channel.
        """
        up = talib.MAX(self.high, n)
        down = talib.MIN(self.low, n)

        if array:
            return up, down
        return up[-1], down[-1]

    def aroon(
        self,
        n: int,
        dev: float,
        array: bool = False
    ):
        """
        Aroon indicator.
        """
        aroon_up, aroon_down = talib.AROON(self.high, self.low, n)

        if array:
            return aroon_up, aroon_down
        return aroon_up[-1], aroon_down[-1]

    def aroonosc(self, n: int, array: bool = False):
        """
        Aroon Oscillator.
        """
        result = talib.AROONOSC(self.high, self.low, n)

        if array:
            return result
        return result[-1]

    def minus_dm(self, n: int, array: bool = False):
        """
        MINUS_DM.
        """
        result = talib.MINUS_DM(self.high, self.low, n)

        if array:
            return result
        return result[-1]

    def plus_dm(self, n: int, array: bool = False):
        """
        PLUS_DM.
        """
        result = talib.PLUS_DM(self.high, self.low, n)

        if array:
            return result
        return result[-1]

    def mfi(self, n: int, array: bool = False):
        """
        Money Flow Index.
        """
        result = talib.MFI(self.high, self.low, self.close, self.volume, n)
        if array:
            return result
        return result[-1]

    def ad(self, n: int, array: bool = False):
        """
        AD.
        """
        result = talib.AD(self.high, self.low, self.close, self.volume, n)
        if array:
            return result
        return result[-1]

    def adosc(self, n: int, array: bool = False):
        """
        ADOSC.
        """
        result = talib.ADOSC(self.high, self.low, self.close, self.volume, n)
        if array:
            return result
        return result[-1]

    def bop(self, array: bool = False):
        """
        BOP.
        """
        result = talib.BOP(self.open, self.high, self.low, self.close)

        if array:
            return result
        return result[-1]


@lru_cache(maxsize=999)
def load_bar_data(
    pool: Tuple,
    start: datetime,
    end: datetime
):
    """"""
    leg_bars: Dict[str,Dict] = {}
    for vt_symbol in pool:
        bar_data = database_manager.load_bar_data(vt_symbol,start,end)
        bars = {bar.datetime: bar for bar in bar_data}
        leg_bars[vt_symbol] = bars

    bardict:Dict[datetime,Dict] = {}

    for dt in bars.keys():
        temp = {}
        for vt_symbol in pool:
            leg_bar = leg_bars[vt_symbol].get(dt,None)
            if leg_bar:
                temp[vt_symbol] = leg_bar
        bardict[dt] = temp

    return bardict


def extract_vt_symbol(vt_symbol: str) -> Tuple[str, Exchange]:
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_str = vt_symbol.split(".")
    return symbol, Exchange(exchange_str)


def virtual(func: Callable) -> Callable:
    """"""
    return func
