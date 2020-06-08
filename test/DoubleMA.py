from bkt.template import Template
from typing import List,Dict
from bkt.base import Bar,OrderData,TradeData
from bkt.func import BarManager
from bkt.constant import Offset
from bkt.base import Position
from bkt.func import BarGenerator


class DoubleMAStrategy(Template):
    """
    Double MA Strategy
    params:MA5: 5days moving average
           MA10: 10days moving average
    """
    author = "Bohr"

    fast_window = 10
    slow_window = 20

    fast_ma0 = 0.0
    fast_ma1 = 0.0

    slow_ma0 = 0.0
    slow_ma1 = 0.0

    if_pos = 0
    ic_pos = 0

    parameters: List[str] = ['fast_window',
                             'slow_window']
    open_allow = True
    variables: List[str] = ['fast_ma0',
                            'fast_ma1',
                            'slow_ma0',
                            'slow_ma1',
                            'open_allow']

    def __init__(self,
                 engine,
                 setting: Dict):
        """"""
        super().__init__(engine=engine,setting=setting)
        self.bg = BarGenerator(on_bar=self.on_bar,window=5,on_window_bar=self.on_x_bar)
        self.bm = BarManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.output("策略初始化")
        self.load_bar(10)

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
        ratio = self.bars['if'].close / self.bars['ic'].close
        price_ratio = Bar(time=self.bars['if'].datetime,
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

        fast_ma = self.bm.sma(self.fast_window,array=True)
        self.fast_ma0 = fast_ma[-1]
        self.fast_ma1 = fast_ma[-2]

        slow_ma = self.bm.sma(self.slow_window,array=True)
        self.slow_ma0 = slow_ma[-1]
        self.slow_ma1 = slow_ma[-2]

        long_signal = self.fast_ma0 > self.slow_ma0 and self.fast_ma1 < self.slow_ma1
        short_signal = self.fast_ma0 < self.slow_ma0 and self.fast_ma1 > self.slow_ma1

        if long_signal and self.open_allow:
            self.long(self.bars['if'].vt_symbol,self.bars['if'].close,5,300)
            self.short(self.bars['ic'].vt_symbol,self.bars['ic'].close,5,300)

        if short_signal and not self.open_allow:
            self.close(self.bars['if'].vt_symbol, self.bars['if'].close, 5)
            self.cover(self.bars['ic'].vt_symbol, self.bars['ic'].close, 5)

    def on_pos(self,pos:Position):
        """
        Callback when position is updated.
        """
        pass

    def on_order(self, order: OrderData):
        """
        Callback when order status is updated.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback when new trade data is received.
        """
        if trade.offset == Offset.OPEN or trade.offset == Offset.SHORT:
            self.open_allow = False
        else:
            self.open_allow = True


