from datetime import datetime,date
from typing import Dict
from bkt.constant import Direction, Offset,Status,TradeType
from math import floor
import pandas as pd
import numpy as np


class Tick:
    """"""
    def __init__(self,
                 time:datetime,
                 vt_symbol:str,
                 last_price:float=0.,
                 last_volume:int=0,
                 open:float=0.,
                 open_interest:float=0.,
                 bid:float=0.,
                 bid_volume:int=0,
                 ask:float=0.,
                 ask_volume:int=0,
                 multiplier:int=1):
        self.datetime = time
        self.vt_symbol = vt_symbol
        self.last_price = last_price
        self.last_volume = last_volume
        self.open = open
        self.open_interest = open_interest
        self.last_volume = last_volume
        self.bid = bid
        self.bid_volume = bid_volume
        self.ask = ask
        self.ask_volume = ask_volume
        self.multiplier = multiplier


class Bar:
    """"""
    def __init__(self,
                 time:datetime,
                 vt_symbol:str,
                 open:float=0.,
                 open_interest:float=0.,
                 high:float=0.,
                 low:float=0.,
                 close:float=0.,
                 volume:int=0,
                 multiplier:int=1):
        self.datetime = time
        self.vt_symbol = vt_symbol
        self.open = open
        self.open_interest = open_interest
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.multiplier = multiplier


class OrderData:
    """"""
    def __init__(self,
                 time:datetime,
                 vt_symbol:str,
                 direction:Direction,
                 offset:Offset,
                 price:float,
                 volume:int,
                 multiplier:int,
                 orderid:str):
        self.datetime = time
        self.vt_symbol = vt_symbol
        self.direction = direction
        self.offset = offset
        self.status = Status.SUBMITTING
        self.price = price
        self.volume = volume
        self.multiplier =  multiplier
        self.orderid = orderid

    def is_active(self):
        """"""
        if self.status not in [Status.CANCELLED, Status.ALLTRADED]:
            return True
        else:
            return False


class TradeData:
    """"""
    def __init__(self,
                 time:datetime,
                 vt_symbol,
                 direction:Direction,
                 offset: Offset,
                 price:float,
                 volume:int,
                 multiplier:int,
                 orderid:str,
                 tradeid:str):
        self.datetime = time
        self.vt_symbol = vt_symbol
        self.direction = direction
        self.offset = offset
        self.price = price
        self.volume = volume
        self.multiplier =  multiplier
        self.money = price * volume
        self.orderid = orderid
        self.tradeid = tradeid


class TickerPos:
    """"""
    def __init__(self,
                 date:date,
                 vt_symbol:str,
                 direction:Direction,
                 cost:float,
                 volume:int,
                 multiplier:int=1,
                 trade_type:TradeType=TradeType.T1):

        self.date = date
        self.vt_symbol: str = vt_symbol
        self.direction: Direction = direction
        self.multiplier: int = multiplier
        self.cost: float = cost
        self.volume: int = volume
        self.market_price: float = cost
        self.money: float = cost * volume
        self.value: float = cost * volume
        self.unrealized_pnl: float = 0
        self.realized_pnl: float = 0
        self.trade_type = trade_type
        if trade_type == TradeType.T1:
            self.frozen_volume = volume
            self.tradable = 0
        else:
            self.frozen_volume = 0
            self.tradable = volume

    def update(self,date:date,price:float,volume:int=0):
        self.market_price = price
        if volume > 0:
            self.volume += volume
            self.money += price * volume
            self.cost = self.money / self.volume
            if self.trade_type == TradeType.T1:
                self.frozen_volume += volume
            else:
                self.tradable += volume
        elif volume < 0 :
            self.volume += volume
            self.money += self.cost * volume
            self.tradable += volume

            if self.direction == Direction.LONG:
                self.date = date
                self.realized_pnl = (price - self.cost) * self.multiplier * abs(volume)
            else:
                self.date = date
                self.realized_pnl = (self.cost - price) * self.multiplier * abs(volume)

        self.value = self.market_price * self.volume

        if self.direction == Direction.LONG:
            self.unrealized_pnl = (self.value - self.money) * self.multiplier
        else:
            self.unrealized_pnl = (self.money - self.value) * self.multiplier


class Position:
    """"""
    def __init__(self,trade_type:TradeType=TradeType.T1):
        self.long_pos: Dict[str,TickerPos] = {}
        self.short_pos: Dict[str,TickerPos] = {}
        self.realized_pnl: float = 0
        self.trade_type = trade_type

    def __getitem__(self, vt_symbol: str):
        ticker = self.long_pos.get(vt_symbol,None)
        if ticker:
            return ticker.volume
        else:
            ticker = self.short_pos.get(vt_symbol,None)
        if ticker:
            return ticker.volume
        else:
            return 0

    def long(self,trade:TradeData):
        date = trade.datetime.date()
        vt_symbol = trade.vt_symbol
        price = trade.price
        volume = trade.volume
        multiplier = trade.multiplier
        ticker = self.long_pos.get(vt_symbol,None)
        if not ticker:
            self.long_pos[vt_symbol] = TickerPos(date=date,
                                                 vt_symbol=vt_symbol,
                                                 direction=Direction.LONG,
                                                 cost=price,
                                                 volume=volume,
                                                 multiplier=multiplier,
                                                 trade_type=self.trade_type)
        else:
            ticker.update(date=date,price=price,volume=volume)
            
        return True

    def short(self,trade:TradeData):
        date = trade.datetime.date()
        vt_symbol = trade.vt_symbol
        price = trade.price
        volume = trade.volume
        multiplier = trade.multiplier
        ticker = self.short_pos.get(vt_symbol, None)
        if not ticker:
            self.short_pos[vt_symbol] = TickerPos(date=date,
                                                  vt_symbol=vt_symbol,
                                                  direction=Direction.SHORT,
                                                  cost=price,
                                                  volume=volume,
                                                  multiplier=multiplier,
                                                  trade_type=self.trade_type)
        else:
            ticker.update(date=date,price=price,volume=volume)

        return True

    def close(self,trade:TradeData):
        date = trade.datetime.date()
        vt_symbol = trade.vt_symbol
        price = trade.price
        volume = trade.volume
        ticker = self.long_pos.get(vt_symbol, None)
        if not ticker:
            return False
        else:
            if ticker.tradable == 0:
                return
            elif abs(volume) > ticker.tradable:
                volume = ticker.tradable
                trade.volume = volume
            ticker.update(date=date,price=price, volume=-volume)
            self.realized_pnl += ticker.realized_pnl
        if not ticker.volume:
            self.long_pos.pop(vt_symbol)
            
        return True

    def cover(self,trade:TradeData):
        date = trade.datetime.date()
        vt_symbol = trade.vt_symbol
        price = trade.price
        volume = trade.volume
        ticker = self.short_pos.get(vt_symbol, None)
        if not ticker:
            return False
        else:
            if ticker.tradable == 0:
                return
            elif abs(volume) > ticker.tradable:
                volume = ticker.tradable
                trade.volume = volume
            ticker.update(date=date,price=price, volume=-volume)
            self.realized_pnl += ticker.realized_pnl
        if not ticker.volume:
            self.short_pos.pop(vt_symbol)
        
        return True
    
    def update_tick(self,tick:Tick):
        d = tick.datetime.date()
        vt_symbol = tick.vt_symbol
        ticker = self.long_pos.get(vt_symbol, None)
        if ticker:
            if d != ticker.date:
                ticker.tradable += ticker.frozen_volume
                ticker.frozen_volume = 0
            ticker.update(date=d, price=tick.last_price)

        ticker = self.short_pos.get(vt_symbol, None)
        if ticker:
            if d != ticker.date:
                ticker.tradable += ticker.frozen_volume
                ticker.frozen_volume = 0
            ticker.update(date=d, price=tick.last_price)

    def update_bar(self,bar:Bar):
        d = bar.datetime.date()
        vt_symbol = bar.vt_symbol
        ticker = self.long_pos.get(vt_symbol,None)
        if ticker:
            if d != ticker.date:
                ticker.tradable += ticker.frozen_volume
                ticker.frozen_volume = 0
            ticker.update(date=d, price=bar.close)

        ticker = self.short_pos.get(vt_symbol,None)
        if ticker:
            if d != ticker.date:
                ticker.tradable += ticker.frozen_volume
                ticker.frozen_volume = 0
            ticker.update(date=d, price=bar.close)

    @property
    def frozen(self):
        _frozen = 0
        for ticker in self.long_pos.values():
            _frozen += ticker.money
        for ticker in self.short_pos.values():
            _frozen += ticker.money
        return _frozen

    @property
    def unrealized_pnl(self):
        _unrealized_pnl = 0
        for ticker in self.long_pos.values():
            _unrealized_pnl += ticker.unrealized_pnl
        for ticker in self.short_pos.values():
            _unrealized_pnl += ticker.unrealized_pnl
        return _unrealized_pnl


class Account:
    """"""
    def __init__(self,
                 capital:float=1000000,
                 rate:float=3/10000,
                 slippage:float=0,
                 trade_type:TradeType=TradeType.T1):
        self.position: Position = Position(trade_type)
        self.capital: float = capital
        self.rate: float = rate
        self.slippage: float = slippage
        self.total_commission:float = 0
        self.total_slippage: float = 0
        self.daily_result: Dict[date,float] = {}
        self.total_trade_count: int = 0
        self.trade_type: TradeType = trade_type


    def max_open(self,capital:float,price:float):
        commission = price * self.rate
        vol = floor(capital / (commission + self.slippage + price))
        return vol

    def max_sell(self,vt_symbol:str):
        ticker = self.position.long_pos.get(vt_symbol,0)
        if not ticker:
            return 0
        else:
            return ticker.tradable

    def max_cover(self,vt_symbol):
        ticker = self.position.short_pos.get(vt_symbol, 0)
        if not ticker:
            return 0
        else:
            return ticker.tradable

    def update_pos(self,trade:TradeData):
        flag = False

        if trade.offset == Offset.OPEN:
            flag = self.position.long(trade)
        elif trade.offset == Offset.SHORT:
            flag = self.position.short(trade)
        elif trade.offset == Offset.CLOSE:
            flag = self.position.close(trade)
        elif trade.offset == Offset.COVER:
            flag = self.position.cover(trade)
        if flag:
            self.total_commission += self.rate * trade.price * trade.volume
            self.total_slippage += self.slippage * trade.volume * trade.multiplier
            self.total_trade_count += trade.volume

        return flag

    def update_tick(self,tick:Tick):
        self.position.update_tick(tick)

    def update_bar(self,bar:Bar):
        self.position.update_bar(bar)

    def update_daily(self,d:date):
        self.daily_result.update({d:self.equity})

    def calculate_statistic(self):
        if not self.daily_result:
            return
        df = pd.DataFrame(self.daily_result.items(),columns=['date','equity']).set_index('date')
        self.daily_result = df
        df['return'] = np.log(df['equity'] / (df['equity'].shift(1))).fillna(0)
        df['highlevel'] = (df['equity'].rolling(min_periods=1,window=len(df),center=False).max())
        df['drawdown'] = df['equity'] - df['highlevel']
        df['ddpercent'] = df['drawdown'] / df['highlevel'] *100

        start_date = df.index[0]
        end_date = df.index[-1]
        total_days = len(df)
        profit_days = len(df[df['return'] > 0])
        loss_days = len(df[df['return'] < 0])

        end_euiqty = df['equity'].iloc[-1]
        max_drawdown = df['drawdown'].min()
        max_ddpercent = df['ddpercent'].min()
        max_drawdown_end = df['drawdown'].idxmin()
        max_drawdown_start= df['equity'][:max_drawdown_end].idxmax()
        max_drawdown_duration = (max_drawdown_end - max_drawdown_start).days

        total_net_pnl = end_euiqty - self.capital
        daily_net_pnl = total_net_pnl / total_days

        total_commission = self.total_commission
        daily_commission = total_commission / total_days

        total_slippage = self.slippage
        daily_slippage = total_slippage / total_days

        total_turnover = self.total_commission / self.rate
        daily_turnover = total_turnover / total_days

        total_trade_count = self.total_trade_count
        daily_trade_count = total_trade_count / total_days

        total_return = (end_euiqty / self.capital - 1) * 100
        annual_return = total_return / total_days * 240
        daily_return = df['return'].mean() * 100
        return_std = df['return'].std() * 100

        if return_std:
            sharpe_ratio = annual_return / (return_std * np.sqrt(240))
        else:
            sharpe_ratio = 0

        return_drawdown_ratio = -total_return / max_ddpercent

        statistcs = {"start_date":start_date,
                     "end_date":end_date,
                     "total_days":total_days,
                     "profit_days":profit_days,
                     "loss_days":loss_days,
                     "capital":self.capital,
                     "end_equity":end_euiqty,
                     "max_drawdown":max_drawdown,
                     "max_drawdown_duration":max_drawdown_duration,
                     "total_net_pnl":total_net_pnl,
                     "daily_net_pnl":daily_net_pnl,
                     "total_commission":total_commission,
                     "daily_commission":daily_commission,
                     "total_slippage":total_slippage,
                     "daily_slippage":daily_slippage,
                     "total_turnover":total_turnover,
                     "daily_turnover":daily_turnover,
                     "total_trade_count":total_trade_count,
                     "daily_trade_count":daily_trade_count,
                     "total_return":total_return,
                     "annual_return":annual_return,
                     "daily_return":daily_return,
                     "return_std":return_std,
                     "sharpe_ratio":sharpe_ratio,
                     "return_drawdown_ratio":return_drawdown_ratio}

        return statistcs,df

    @property
    def equity(self):
        return self.available + self.unrealized_pnl + self.frozen

    @property
    def available(self):
        return self.capital + self.profit - self.frozen

    @property
    def profit(self):
        return self.position.realized_pnl - self.total_slippage - self.total_commission

    @property
    def frozen(self):
        return self.position.frozen

    @property
    def unrealized_pnl(self):
        return self.position.unrealized_pnl





