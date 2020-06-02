from bkt.template import Template
from typing import List,Dict
from bkt.base import Bar
from bkt.func import BarManager
from bkt.base import Position
from bkt.func import BarGenerator


class BBStrategy(Template):
    """

    """
    author = "Bohr"

    trailMALength = 20
    bbOrder = 2.4

    parameters: List[str] = ["trailMALength",
                             "bbOrder"]

    up = 0
    mid = 0
    down = 0
    leading_pos = 0
    hedging_pos = 0

    variables: List[str] = ["up",
                            "mid",
                            "down",
                            "leading_pos",
                            "hedging_pos"]

    def __init__(self,
                 engine,
                 setting: Dict):
        """"""
        super().__init__(engine=engine,setting=setting)
        self.bg = BarGenerator(on_bar=self.on_bar,window=5,on_window_bar=self.on_x_bar)
        self.bm = BarManager(150)
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
        ratio = self.leading_bar.close / self.hedging_bar.close
        price_ratio = Bar(time=self.leading_bar.datetime,
                          vt_symbol='spread',
                          open=ratio,
                          high=ratio,
                          low=ratio,
                          close=ratio,
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

        self.up,self.mid,self.down = self.bm.boll(self.trailMALength,self.bbOrder)
        if self.leading_pos + self.hedging_pos == 0:
            if bar.close > self.up:
                allowcate = self.available / (2*300)
                leading_allowcate = self.max_open(allowcate,self.leading_bar.close)
                hedging_allowcate = self.max_open(allowcate,self.hedging_bar.close)
                self.long('if',self.leading_bar.close,leading_allowcate,300)
                self.short('ic',self.hedging_bar.close,hedging_allowcate,300)

        if self.leading_pos + self.hedging_pos != 0:
            if bar.close < self.mid:
                self.close('if',self.leading_bar.close,self.leading_pos)
                self.cover('ic',self.hedging_bar.close,self.hedging_pos)

    def on_pos(self,pos:Position):
        """
        Callback when position is updated.
        """
        self.leading_pos = pos['if']
        self.hedging_pos = pos['ic']




