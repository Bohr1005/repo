from bkt.template import Template
from typing import List,Dict
from bkt.base import Bar
from bkt.base import Position
from bkt.func import BarGenerator,BarManager


class BotBarManager(BarManager):
    def __init__(self,size=100):
        super(BotBarManager, self).__init__(size=size)

    def Accl(self,fa,sa):
        sumf = (self.close[-fa:] - self.open[-fa:]).mean()
        sums = (self.close[-fa-sa:-fa] - self.open[-fa-sa:-fa]).mean()
        if sums == 0:
            return 0
        return sumf / sums


class BotStrategy(Template):
    """

    """
    author = "Bohr"

    fa = 2
    sa = 8
    ratio = 0.005
    accl = 2

    parameters: List[str] = ["fa",
                             "sa",
                             "ratio",
                             "accl"]

    leading_pos = 0
    hedging_pos = 0
    mainStoploss = 0

    variables: List[str] = ["leading_pos",
                            "hedging_pos",
                            "mainStoploss"]

    def __init__(self,
                 engine,
                 setting: Dict):
        """"""
        super().__init__(engine=engine,setting=setting)
        self.bg = BarGenerator(on_bar=self.on_bar,window=5,on_window_bar=self.on_x_bar)
        self.bm = BotBarManager(150)
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
        self.leading_bar = self.bars[self.leading_leg]
        self.hedging_bar = self.bars[self.hedging_leg]
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

        ca = self.bm.Accl(self.fa,self.sa)

        if self.leading_pos + self.hedging_pos == 0:
            if ca > self.accl:
                allowcate = self.available / (2*300)
                leading_allowcate = self.max_open(allowcate,self.leading_bar.close)
                hedging_allowcate = self.max_open(allowcate,self.hedging_bar.close)
                self.long(self.leading_leg,self.leading_bar.close,leading_allowcate,300)
                self.short(self.hedging_leg,self.hedging_bar.close,hedging_allowcate,300)
                self.mainStoploss = (1 - self.ratio) * self.equity

        if self.leading_pos + self.hedging_pos != 0:
            if self.equity < self.mainStoploss:
                self.close(self.leading_leg,self.leading_bar.close,self.leading_pos)
                self.cover(self.hedging_leg,self.hedging_bar.close,self.hedging_pos)

            elif self.mainStoploss < self.equity * (1 - self.ratio):
                self.mainStoploss = (1 - self.ratio) * self.equity

    def on_pos(self,pos:Position):
        """
        Callback when position is updated.
        """
        self.leading_pos = pos[self.leading_leg]
        self.hedging_pos = pos[self.hedging_leg]




