from bkt.engine import BacktestingEngine
from datetime import datetime,time
from bkt.constant import TradeType
from strategy.BB import BBStrategy
from strategy.REVERSAL import REVERSALStrategy


pool = ('if','ic')
engine = BacktestingEngine()
engine.set_parameters(pool=pool,
                      interval='1m',
                      start_date=datetime(2016,1,1),
                      rate=3/10000,
                      slippage=0,
                      capital=10000000,
                      end_date=datetime(2020,1,1),
                      start_time=time(hour=9, minute=30),
                      end_time=time(hour=14, minute=55),
                      trade_type=TradeType.T1)

engine.add_strategy(REVERSALStrategy,{})
engine.load_data()
engine.run_backtesting()
engine.calculate_statistics()
engine.show_chart()
for trade in engine.trades.values():
    print(trade.__dict__)
