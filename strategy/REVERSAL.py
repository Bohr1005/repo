from bkt.template import Template
from typing import List,Dict
from bkt.base import Bar
from bkt.base import Position
from bkt.func import BarGenerator,BarManager
import numpy as np


class REVERSALBarManager(BarManager):
    def __init__(self,size=100):
        super(REVERSALBarManager, self).__init__(size=size)

    def HightAndLowest(self,short,long):
        hightest0 = np.max(self.high[-short:])
        hightest1 = np.max(self.high[-long:-short])
        lowest0 = np.min(self.low[-short:])
        lowest1 = np.min(self.low[-long:-short])
        return hightest0,hightest1,lowest0,lowest1


class REVERSALStrategy(Template):
    """
    """
    author = "Bohr"

    bbLength =15
    bbOrder = 1.5
    shortBar = 21
    longBar = 81
    atrEntryOrder = 3.5
    ATRLength = 20
    ratio = 0.005

    parameters: List[str] = ["bbLength",
                             "bbOrder",
                             "shortBar",
                             "longBar",
                             "atrEntryOrder",
                             "ATRLength",
                             "ratio"]

    leading_pos = 0
    hedging_pos = 0
    mainStoploss= 0

    variables: List[str] = ["leading_pos",
                            "hedging_pos",
                            "mainStoploss"]

    def __init__(self,
                 engine,
                 setting: Dict):
        """"""
        super().__init__(engine=engine,setting=setting)
        self.bg = BarGenerator(on_bar=self.on_bar,window=5,on_window_bar=self.on_x_bar)
        self.bm = REVERSALBarManager(150)
        self.leading_bar = None
        self.hedging_bar = None

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.output("策略初始化")
        self.load_bar(30)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.output("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.output("策略停止")

    def on_tick(self):
        """
        Callback when new tick data is generated.
        """
        pass

    def on_bar(self):
        """
        Callback when new bar data is generated.
        """
        self.leading_bar = self.bars['if']
        self.hedging_bar = self.bars['ic']
        ratio_open = self.leading_bar.open / self.hedging_bar.open
        ratio_close = self.leading_bar.close / self.hedging_bar.close

        price_ratio = Bar(time=self.leading_bar.datetime,
                          vt_symbol='spread',
                          open=ratio_open,
                          high=ratio_close,
                          low=ratio_close,
                          close=ratio_close,
                          open_interest=0,
                          volume=0)

        self.bg.update_bar(price_ratio)

    def on_x_bar(self,bar: Bar):
        """
        Callback when price ratio data on other period is generated
        """
        self.bm.update_bar(bar)
        if not self.bm.inited or not self.trading:
            return

        up,_,down = self.bm.boll(self.bbLength,self.bbOrder)
        high_short,high_long,low_short,low_long = self.bm.HightAndLowest(self.shortBar,self.longBar)
        long_trend = (high_short > high_long and low_short > low_long)
        short_trend = (high_long < high_long and low_short < low_long)

        bollinger_buy = (self.bm.close[-2] < down and self.bm.close[-1] > down)
        bollinger_sell = (self.bm.close[-2] > up and self.bm.close[-1] < up)

        atr = self.bm.atr(self.ATRLength)
        updown = up - down

        buy_signal = (long_trend and bollinger_buy and updown < atr * self.atrEntryOrder)
        sell_signal = (short_trend and bollinger_sell and updown < atr * self.atrEntryOrder)

        if (self.leading_pos + self.hedging_pos == 0 and buy_signal):
            allowcate = self.available / (2 * 300)
            leading_allowcate = self.max_open(allowcate, self.leading_bar.close)
            hedging_allowcate = self.max_open(allowcate, self.hedging_bar.close)
            self.long('if', self.leading_bar.close, leading_allowcate, 300)
            self.short('ic', self.hedging_bar.close, hedging_allowcate, 300)
            self.mainStoploss = (1 - self.ratio) * self.equity

        if (self.leading_pos + self.hedging_pos == 0 and sell_signal):
            allowcate = self.available / (2 * 300)
            leading_allowcate = self.max_open(allowcate, self.leading_bar.close)
            hedging_allowcate = self.max_open(allowcate, self.hedging_bar.close)
            self.short('if', self.leading_bar.close, leading_allowcate, 300)
            self.long('ic', self.hedging_bar.close, hedging_allowcate, 300)
            self.mainStoploss = (1 - self.ratio) * self.equity

        if self.leading_pos + self.hedging_pos != 0:
            if self.equity < self.mainStoploss:
                self.close('if', self.leading_bar.close, self.leading_pos)
                self.cover('if', self.leading_bar.close, self.leading_pos)
                self.close('ic', self.hedging_bar.close, self.hedging_pos)
                self.cover('ic', self.hedging_bar.close, self.hedging_pos)

            elif self.mainStoploss < self.equity * (1 - self.ratio):
                self.mainStoploss = (1 - self.ratio) * self.equity

    def on_pos(self,pos:Position):
        """
        Callback when position is updated.
        """
        self.leading_pos = pos['if']
        self.hedging_pos = pos['ic']




