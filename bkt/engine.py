from datetime import datetime,time
from bkt.constant import Status,BacktestingMode,Interval, Offset,Direction,TradeType
from bkt.base import Account,OrderData,TradeData,Tick,Bar
from bkt.optimization_setting import OptimizationSetting
from bkt.func import load_bar_data
import matplotlib.pyplot as plt
from typing import Callable,Tuple,Dict
from deap import base,tools,creator,algorithms
import numpy as np
from functools import lru_cache
import random
from pandas import DataFrame


creator.create("FitnessMax",base.Fitness,weights=(1.0,))
creator.create("Individual",list,fitness=creator.FitnessMax)


def optimize(
    target_name,
    strategy_class,
    setting,
    pool,
    interval,
    start_date:datetime,
    end_date:datetime,
    start_time:time,
    end_time:time,
    rate,
    slippage,
    capital):

    engine = BacktestingEngine()
    engine.set_parameters(
        pool=pool,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        rate=rate,
        slippage=slippage,
        capital=capital
    )
    engine.add_strategy(strategy_class, setting)
    engine.load_data()
    engine.run_backtesting()
    statistics = engine.calculate_statistics(output=False)
    target_value = statistics[target_name]

    return str(setting), target_value, statistics


@lru_cache(maxsize=999)
def _ga_optimize(parameter_values):
    ga_setting = dict(parameter_values)

    result = optimize(target_name=ga_target_name,
                      strategy_class=ga_strategy_class,
                      setting=ga_setting,
                      pool=ga_pool,
                      interval=ga_interval,
                      start_date=ga_start_date,
                      end_date=ga_end_date,
                      start_time=ga_start_time,
                      end_time=ga_end_time,
                      rate=ga_rate,
                      slippage=ga_slippage,
                      capital=ga_capital
                      )

    return (result[1],)


def ga_optimizie(parameter_values:list):
    return _ga_optimize(tuple(parameter_values))


class BacktestingEngine:
    """"""
    def __init__(self):
        """"""
        self.start_date = None
        self.end_date = None
        self.start_time = None
        self.end_time = None
        self.pool = None

        self.capital = 1000000
        self.rate = 3/10000
        self.slippage = 0

        self.mode = BacktestingMode.BAR
        self.account = Account()

        self.strategy_class = None
        self.strategy = None
        self.ticks: Dict[str,Tick] = None
        self.bars: Dict[str,Bar] = None
        self.datetime = None
        self.start_time = None
        self.end_time = None

        self.interval = None
        self.days = 0
        self.callback = None
        self.history_data = {}

        self.order_count = 0
        self.orders: Dict[str,OrderData] = {}
        self.active_orders: Dict[str,OrderData] = {}

        self.trade_count = 0
        self.trades: Dict[str,TradeData] = {}

    @staticmethod
    def output(msg):
        """
        Output message of backtesting engine.
        """
        print(f"{datetime.now()}\t{msg}")

    def clear_data(self):
        """
        Clear all data of last backtesting.
        """
        self.strategy = None
        self.ticks = None
        self.bars = None
        self.datetime = None
        self.start_time = None
        self.end_time = None

        self.order_count = 0
        self.orders.clear()
        self.active_orders.clear()

        self.trade_count = 0
        self.trades.clear()

    def set_parameters(
        self,
            pool: Tuple,
            interval: str,
            start_date: datetime,
            rate: float,
            slippage: float = 0,
            capital: float = 0,
            end_date: datetime = None,
            start_time: time = time(hour=9, minute=30, second=0, microsecond=0),
            end_time: time = time(hour=14, minute=55, second=0, microsecond=0),
            trade_type: TradeType = TradeType.T1,
            mode: object = BacktestingMode.BAR):
        """"""
        self.pool = pool
        self.interval = Interval(interval)
        self.start_date = start_date
        self.end_date = end_date
        self.start_time = start_time
        self.end_time = end_time
        self.rate = rate
        self.slippage = slippage
        self.capital = capital
        self.account = Account(capital=capital,rate=rate,slippage=slippage,trade_type=trade_type)
        self.mode = mode

    def add_strategy(self, strategy_class: type, setting: dict):
        """"""
        self.strategy_class = strategy_class

        self.strategy = strategy_class(
            self,
            setting)

    def add_pair(self,leading_leg:str,hedging_leg:str):
        self.strategy.leading_leg = leading_leg
        self.strategy.hedging_leg = hedging_leg

    def load_data(self):
        """"""
        self.output("开始加载历史数据")
        if not self.end_date:
            self.end_date = datetime.now()

        if self.start_date >= self.end_date:
            self.output("起始日期必须小于结束日期")
            return
        self.history_data.clear()
        self.history_data = load_bar_data(
            self.pool,
            self.start_date,
            self.end_date
        )
        self.output(f"历史数据加载完成，数据量：{len(self.history_data) * len(self.pool)}")

    def run_backtesting(self,lantency=False):
        """"""
        if self.mode == BacktestingMode.BAR:
            func = self.new_bar
        else:
            func = self.new_tick

        self.strategy.on_init()
        # Use the first [days] of history data for initializing strategy
        day_count = 0
        ix = 0
        for idx,data in enumerate(self.history_data.items()):
            if self.datetime and data[0].day != self.datetime.day:
                day_count += 1
                if day_count >= self.days:
                    break
            self.datetime = data[0]
            if self.mode == BacktestingMode.BAR:
                self.strategy.bars = data[1]
            else:
                self.strategy.ticks = data[1]
            self.callback()

        self.strategy.inited = True
        self.output("策略初始化完成")

        self.strategy.on_start()
        self.strategy.trading = True
        self.output("开始回放历史数据")

        # Use the rest of history data for running backtesting
        for bars in list(self.history_data.items())[ix:]:
            if self.strategy.equity < 0:
                self.output("权益不足")
                break
            func(bars,lantency=lantency)
        self.output("历史数据回放结束")
        self.strategy.on_stop()

    def update_tick(self,ticks:Dict):
        d = self.datetime.date()
        for tick in ticks.values():
            self.account.update_tick(tick)
        self.account.update_daily(d)

    def update_bar(self, bars: Dict):
        d = self.datetime.date()
        for bar in bars.values():
            self.account.update_bar(bar)
        self.account.update_daily(d)

    def calculate_statistics(self,output=True):
        statistcs,df = self.account.calculate_statistic()
        if output:
            self.output('-' * 30)
            self.output(f"首个交易日:\t {statistcs['start_date']}")
            self.output(f"最后交易日:\t {statistcs['end_date']}")

            self.output(f"总交易日:\t{statistcs['total_days']}")
            self.output(f"盈利交易日:\t{statistcs['profit_days']}")
            self.output(f"亏损交易日:\t{statistcs['loss_days']}")

            self.output(f"起始资产:\t{statistcs['capital']}")
            self.output(f"结束资产:\t{statistcs['end_equity']}")

            self.output(f"总收益率:\t{statistcs['total_return']}%")
            self.output(f"年化收益:\t{statistcs['annual_return']}%")
            self.output(f"最大回撤:\t{statistcs['max_drawdown']}")
            self.output(f"最长回撤天数:\t{statistcs['max_drawdown_duration']}")

            self.output(f"总盈亏:\t{statistcs['total_net_pnl']}")
            self.output(f"总手续费:\t{statistcs['total_commission']}")
            self.output(f"总滑点:\t{statistcs['total_slippage']}")
            self.output(f"总成交金额:\t{statistcs['total_turnover']}")
            self.output(f"总成交笔数:\t{statistcs['total_trade_count']}")

            self.output(f"日均盈亏:\t{statistcs['daily_net_pnl']}")
            self.output(f"日均手续费:\t{statistcs['daily_commission']}")
            self.output(f"日均滑点:\t{statistcs['daily_slippage']}")
            self.output(f"日均成交金额:\t{statistcs['daily_turnover']}")
            self.output(f"日均成交笔数:\t{statistcs['daily_trade_count']}")

            self.output(f"日均收益率:\t{statistcs['daily_return']}")
            self.output(f"收益率标准差:\t{statistcs['return_std']}")
            self.output(f"Sharpe Ratio:\t{statistcs['sharpe_ratio']}")
            self.output(f"收益回撤比:\t{statistcs['return_drawdown_ratio']}")

        return statistcs

    def show_chart(self,df:DataFrame=None,save_path=None,show=True):
        if df is None:
            df = self.account.daily_result

        fig = plt.figure(figsize=(10,8))
        balance_plot = plt.subplot(1,1,1)
        balance_plot.set_title('equity')
        df['equity'].plot(legend=True)
        if show:
            plt.show()
        if save_path:
            fig.savefig(save_path)

    def new_tick(self,ticks:Tuple,lantency=False):
        self.ticks = ticks[1]
        self.datetime = ticks[0]
        self.update_tick(ticks[1])
        if self.start_time < ticks[0].time() < self.end_time:
            self.strategy.trading = True
        else:
            self.strategy.trading = False

        if lantency:
            self.cross_order()
            self.strategy.ticks = ticks[1]
            self.strategy.on_tick()
        else:
            self.strategy.ticks = ticks[1]
            self.strategy.on_tick()
            self.cross_order()

    def new_bar(self, bars: Tuple,lantency=False):
        """"""
        self.bars = bars[1]
        self.datetime = bars[0]
        self.update_bar(bars[1])
        if self.start_time < bars[0].time() < self.end_time:
            self.strategy.trading = True
        else:
            self.strategy.trading = False

        if lantency:
            self.cross_order()
            self.strategy.bars = bars[1]
            self.strategy.on_bar()
        else:
            self.strategy.bars = bars[1]
            self.strategy.on_bar()
            self.cross_order()

    def cross_order(self):
        """
        Cross limit order with last bar/tick data.
        """
        for order in list(self.active_orders.values()):
            # Check whether limit orders can be filled.
            vt_symbol = order.vt_symbol
            bar = self.bars.get(vt_symbol,None)
            if not bar:
                continue
            long_cross = (
                (order.offset == Offset.OPEN or order.offset == Offset.COVER)
                and order.price >= bar.close + self.slippage
            )

            short_cross = (
                (order.offset == Offset.SHORT or order.offset == Offset.CLOSE)
                and order.price <= bar.close - self.slippage
            )

            if not long_cross and not short_cross:
                order.status = Status.CANCELLED
                self.strategy.update_order(order)
                self.active_orders.pop(order.orderid)
                continue

            # Push trade update
            self.trade_count += 1

            trade = TradeData(time=bar.datetime,
                              vt_symbol=vt_symbol,
                              direction=order.direction,
                              offset=order.offset,
                              price=bar.close,
                              volume=order.volume,
                              multiplier=order.multiplier,
                              orderid=order.orderid,
                              tradeid=str(self.trade_count))

            if self.account.update_pos(trade):
                # Push order update with status "all traded" (filled).
                order.status = Status.ALLTRADED
                self.trades[trade.tradeid] = trade
                self.strategy.on_trade(trade)
                self.strategy.on_pos(self.account.position)
            else:
                order.status = Status.CANCELLED
            self.strategy.update_order(order)
            self.active_orders.pop(order.orderid)

    def send_order(
        self,
        vt_symbol,
        price: float,
        volume: int,
        direction: Direction,
        offset: Offset,
        multiplier: int = 1
    ) -> str:
        """"""
        self.order_count += 1
        orderid = str(self.order_count)
        order = OrderData(time=self.datetime,
                          vt_symbol=vt_symbol,
                          direction=direction,
                          offset=offset,
                          price=price,
                          volume=volume,
                          multiplier=multiplier,
                          orderid=orderid
                          )

        self.orders[orderid] = order
        self.active_orders[orderid] = order
        self.strategy.update_order(order)

        return orderid

    def load_bar(self, days: int, callback: Callable):
        """"""
        self.days = days
        self.callback = callback

    def run_optimization(self, optimization_setting: OptimizationSetting, output=True):
        """"""
        # Get optimization setting and target
        settings = optimization_setting.generate_setting()
        target_name = optimization_setting.target_name

        if not settings:
            self.output("优化参数组合为空，请检查")
            return

        if not target_name:
            self.output("优化目标未设置，请检查")
            return

        results = []
        for setting in settings:
            result = optimize(target_name,
                              self.strategy_class,
                              setting,
                              self.pool,
                              self.interval,
                              self.start_date,
                              self.end_date,
                              self.start_time,
                              self.end_time,
                              self.rate,
                              self.slippage,
                              self.capital)

            results.append(result)

        results.sort(reverse=True, key=lambda result: result[1])
        if output:
            for value in results:
                msg = f"参数：{value[0]}, 目标：{value[1]}"
                self.output(msg)

        return results

    def run_ga_optimization(self,optimization_setting:OptimizationSetting,
                            population_size=100,
                            ngen_size=30):

        settings = optimization_setting.generate_ga_setting()
        target_name = optimization_setting.target_name

        if not settings:
            self.output("优化参数组合为空，请检查")

        if not target_name:
            self.output("优化目标未设置，请检查")

        def generate_parameter():
            return random.choice(settings)

        def mutate_individual(individual,indpb):
            size = len(individual)
            paramlist = generate_parameter()
            for i in range(size):
                if random.random() < indpb:
                    individual[i] = paramlist[i]

            return individual,

        global ga_target_name
        global ga_strategy_class
        global ga_pool
        global ga_settings
        global ga_interval
        global ga_start_date
        global ga_end_date
        global ga_start_time
        global ga_end_time
        global ga_rate
        global ga_capital
        global ga_slippage

        ga_target_name = target_name
        ga_strategy_class = self.strategy_class
        ga_pool = self.pool
        ga_settings = settings[0]
        ga_interval = self.interval
        ga_start_date = self.start_date
        ga_end_date = self.end_date
        ga_start_time = self.start_time
        ga_end_time = self.end_time
        ga_rate = self.rate
        ga_capital = self.capital
        ga_slippage = self.slippage

        toolbox = base.Toolbox
        toolbox.register("individual",tools.initIterate,creator.Individual,generate_parameter)
        toolbox.register("population",tools.initRepeat,list,toolbox.individual)
        toolbox.register("mate",tools.cxTwoPoint)
        toolbox.register("mutate",mutate_individual,indpb=1)
        toolbox.register("evaluate",ga_optimizie)
        toolbox.register("select",tools.selNSGA2)

        total_size = len(settings)
        pop_size = population_size
        lambda_ = pop_size
        mu = int(pop_size * 0.8)

        cxpb = 0.95
        mutpb = 1-cxpb
        ngen = ngen_size

        pop = toolbox.population(pop_size)
        hof = tools.ParetoFront()

        stats = tools.Statistics(lambda ind:ind.fitness.values)
        np.set_printoptions(suppress=True)
        stats.register("mean",np.mean,axis=0)
        stats.register("std", np.std, axis=0)
        stats.register("max", np.max, axis=0)
        stats.register("min", np.min, axis=0)

        self.output(f"参数优化空间：{total_size}")
        self.output(f"每代族群总数：{pop_size}")
        self.output(f"优良筛选个数：{mu}")
        self.output(f"迭代次数：{ngen}")
        self.output(f"交叉概率：{cxpb:.0%}")
        self.output(f"突变概率：{mutpb}")

        algorithms.eaMuPlusLambda(
            pop,
            toolbox,
            mu,
            lambda_,
            cxpb,
            mutpb,
            ngen,
            stats,
            halloffame=hof
        )

        results = []
        for parameters_values in hof:
            setting = dict(parameters_values)
            target_value = ga_optimizie(parameter_values=parameters_values)[0]
            results.append((setting,target_value))

            return results

ga_target_name = None
ga_strategy_class = None
ga_pool = None
ga_settings = None
ga_interval = None
ga_start_date = None
ga_end_date = None
ga_start_time = None
ga_end_time = None
ga_rate = None
ga_capital = None
ga_slippage = None

