from bkt.optimization_setting import OptimizationSetting
from bkt.engine import BacktestingEngine
from test.DoubleMA import DoubleMAStrategy
from datetime import datetime,time
from bkt.constant import TradeType


pool = ('ic','if')
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
engine.add_strategy(DoubleMAStrategy,{})
settings = OptimizationSetting()
settings.add_parameter('fast_window',16,20,1)
settings.add_parameter('slow_window',8,15,1)
settings.set_target('sharpe_ratio')
engine.run_optimization(settings)  #暴力搜索
# engine.run_ga_optimization(population_size=5, ngen_size=5) #遗传算法