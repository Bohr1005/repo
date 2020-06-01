from typing import List, Set,Callable
from copy import copy
from bkt.base import Tick,Bar,OrderData,TradeData
from bkt.constant import Direction, Offset
from bkt.func import virtual
from bkt.base import Position


class Template:
    """Strategy Template"""

    parameters: List[str] = []
    variables: List[str] = []

    def __init__(
        self,
        engine,
        setting: dict
    ):
        """"""
        self.engine = engine

        self.inited = False
        self.trading = False

        self.bars: Bar = None
        self.ticks: Tick = None

        self.variables = copy(self.variables)
        self.variables.insert(0, "inited")
        self.variables.insert(1, "trading")

        self.orders: Set[str] = set()

        self.update_setting(setting)

    def update_setting(self, setting: dict):
        """
        Update strategy parameter wtih value in setting dict.
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])

    def get_parameters(self):
        strategy_parameters = {}
        for name in self.parameters:
            strategy_parameters[name] = getattr(self,name)
        return strategy_parameters

    def get_variables(self):
        strategy_variables = {}
        for name in self.variables:
            strategy_variables[name] = getattr(self, name)
        return strategy_variables

    def update_order(self, order: OrderData):
        """
        Callback when order status is updated.
        """
        if not order.is_active() and order.orderid in self.orders:
            self.orders.remove(order.orderid)

        self.on_order(order)

    @virtual
    def on_init(self):
        """
        Callback when strategy is inited.
        """
        pass

    @virtual
    def on_start(self):
        """
        Callback when strategy is started.
        """
        pass

    @virtual
    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        pass

    @virtual
    def on_tick(self):
        """
        Callback when new tick data is generated.
        """
        pass

    @virtual
    def on_bar(self):
        """
        Callback when new bar data is generated.
        """


    @virtual
    def on_pos(self,pos:Position):
        """
        Callback when position is updated.
        """
        pass

    @virtual
    def on_order(self, order: OrderData):
        """
        Callback when order status is updated.
        """
        pass

    @virtual
    def on_trade(self, trade: TradeData):
        """
        Callback when new trade data is received.
        """
        pass

    def send_order(
        self,
        vt_symbol,
        price: float,
        volume: int,
        direction: Direction,
        offset: Offset,
        multiplier:int=1
    ) -> str:
        """"""
        orderid = self.engine.send_order(vt_symbol=vt_symbol,
                                         price=price,
                                         volume=volume,
                                         direction=direction,
                                         offset=offset,
                                         multiplier=multiplier)
        self.orders.add(orderid)
        return orderid

    def long(self,vt_symbol,price: float,volume: int,multiplier:int=1) -> str:
        """"""
        return self.send_order(vt_symbol=vt_symbol,price=price,
                               volume=volume,
                               direction=Direction.LONG,
                               offset=Offset.OPEN,
                               multiplier=multiplier)

    def short(self, vt_symbol, price: float, volume: int,multiplier:int=1) -> str:
        """"""
        return self.send_order(vt_symbol=vt_symbol,
                               price=price,
                               volume=volume,
                               direction=Direction.SHORT,
                               offset=Offset.SHORT,
                               multiplier=multiplier)

    def close(self,vt_symbol,price: float,volume: int,multiplier:int=1) -> str:
        """"""
        return self.send_order(vt_symbol=vt_symbol,
                               price=price,
                               volume=volume,
                               direction=Direction.LONG,
                               offset=Offset.CLOSE,
                               multiplier=multiplier)

    def cover(self, vt_symbol, price: float, volume: int,multiplier:int=1) -> str:
        """"""
        return self.send_order(vt_symbol=vt_symbol,
                               price=price,
                               volume=volume,
                               direction=Direction.SHORT,
                               offset=Offset.COVER,
                               multiplier=multiplier)

    def load_bar(
        self,
        days: int,
        callback: Callable = None,
    ):
        """
        Load historical bar data for initializing strategy.
        """
        if not callback:
            callback = self.on_bar
        self.engine.load_bar(days,callback)

    def output(self,msg):
        self.engine.output(msg)

    def max_open(self,capital,price:float):
        return self.engine.account.max_open(capital,price)

    def max_sell(self,vt_symbol:str):
        return self.engine.account.max_sell(vt_symbol)

    def max_cover(self,vt_symbol):
        return self.engine.account.max_cover(vt_symbol)

    @property
    def available(self):
        return self.engine.account.available

    @property
    def equity(self):
        return self.engine.account.equity

    @property
    def unrealized(self):
        return self.engine.account.unrealized_pnl

    @property
    def profit(self):
        return self.engine.account.profit

    @property
    def frozen(self):
        return self.engine.account.frozen

    @property
    def long_pos(self):
        return self.engine.account.position.long_pos

    @property
    def short_pos(self):
        return self.engine.account.position.short_pos
