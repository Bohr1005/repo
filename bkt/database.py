from datetime import datetime
from typing import List,Sequence, Type
from peewee import *
from bkt.base import Bar,Tick


PATH = "D:/database.db"


class ModelBase(Model):

    def to_dict(self):
        return self.__data__


def init_models(db: Database):
    class DbBarData(ModelBase):
        id = AutoField()
        vt_symbol: str = CharField()
        datetime: datetime = DateTimeField()
        multiplier: int = IntegerField()
        volume: int = IntegerField()
        open_interest: float = FloatField()
        open_price: float = FloatField()
        high_price: float = FloatField()
        low_price: float = FloatField()
        close_price: float = FloatField()

        class Meta:
            database = db
            indexes = ((("datetime","vt_symbol"), True),)

        @staticmethod
        def from_bar(bar: Bar):
            """
            Generate DbBarData object from BarData.
            """
            db_bar = DbBarData()

            db_bar.vt_symbol = bar.vt_symbol
            db_bar.datetime = bar.datetime
            db_bar.volume = bar.volume
            db_bar.open_interest = bar.open_interest
            db_bar.open_price = bar.open
            db_bar.high_price = bar.high
            db_bar.low_price = bar.low
            db_bar.close_price = bar.close
            db_bar.multiplier = bar.multiplier

            return db_bar

        def to_bar(self):
            """
            Generate BarData object from DbBarData.
            """
            bar = Bar(vt_symbol=self.vt_symbol,
                      time=self.datetime,
                      volume=self.volume,
                      open=self.open_price,
                      high=self.high_price,
                      open_interest=self.open_interest,
                      low=self.low_price,
                      close=self.close_price ,
                      multiplier=self.multiplier)
            return bar

        @staticmethod
        def save_all(objs: List["DbBarData"]):
            """
            save a list of objects, update if exists.
            """
            dicts = [i.to_dict() for i in objs]
            with db.atomic():
                for c in chunked(dicts, 50):
                    DbBarData.insert_many(
                        c).on_conflict_replace().execute()

    class DbTickData(ModelBase):
        """
        Tick data for database storage.

        Index is defined unique with (datetime, symbol)
        """

        id = AutoField()

        vt_symbol: str = CharField()
        datetime: datetime = DateTimeField()
        open: float = FloatField()
        open_interest: float = FloatField()
        last_price: float = FloatField()
        last_volume: int = IntegerField()
        bid: float = FloatField()
        ask: float = FloatField()
        bid_volume: int = IntegerField()
        ask_volume: int = IntegerField()
        multiplier: int = IntegerField()

        class Meta:
            database = db
            indexes = ((("datetime","vt_symbol"), True),)

        @staticmethod
        def from_tick(tick: Tick):
            """
            Generate DbTickData object from TickData.
            """
            db_tick = DbTickData()

            db_tick.vt_symbol = tick.vt_symbol
            db_tick.datetime = tick.datetime
            db_tick.last_volume = tick.last_volume
            db_tick.open = tick.open
            db_tick.open_interest = tick.open_interest
            db_tick.last_price = tick.last_price
            db_tick.last_volume = tick.last_volume
            db_tick.bid = tick.bid
            db_tick.ask = tick.ask
            db_tick.bid_volume = tick.bid_volume
            db_tick.ask_volume = tick.ask_volume
            db_tick.multiplier = tick.multiplier

            return db_tick

        def to_tick(self):
            """
            Generate TickData object from DbTickData.
            """
            tick = Tick(vt_symbol=self.vt_symbol,
                        time=self.datetime,
                        open=self.open,
                        open_interest=self.open_interest,
                        last_price=self.last_price,
                        last_volume=self.last_volume,
                        bid=self.bid,
                        ask=self.ask,
                        bid_volume=self.bid_volume,
                        ask_volume=self.ask_volume)

            return tick

        @staticmethod
        def save_all(objs: List["DbTickData"]):
            dicts = [i.to_dict() for i in objs]
            with db.atomic():
                for c in chunked(dicts, 50):
                    DbTickData.insert_many(c).on_conflict_replace().execute()

    db.connect()
    db.create_tables([DbBarData, DbTickData])
    return DbBarData, DbTickData


class SqlManager:
    """"""
    def __init__(self, class_bar: Type[Model], class_tick: Type[Model]):
        self.class_bar = class_bar
        self.class_tick = class_tick

    def load_bar_data(
        self,
        vt_symbol: str,
        start: datetime,
        end: datetime) -> Sequence[Bar]:
        s = (
            self.class_bar.select()
                .where(
                (self.class_bar.vt_symbol == vt_symbol)
                & (self.class_bar.datetime >= start)
                & (self.class_bar.datetime <= end)
            )
            .order_by(self.class_bar.datetime)
        )
        data = [db_bar.to_bar() for db_bar in s]
        return data

    def load_tick_data(self, vt_symbol: str,
                       start: datetime,
                       end: datetime) -> Sequence[Tick]:
        s = (
            self.class_tick.select()
                .where(
                (self.class_tick.vt_symbol == vt_symbol)
                & (self.class_tick.datetime >= start)
                & (self.class_tick.datetime <= end)
            )
            .order_by(self.class_tick.datetime)
        )

        data = [db_tick.to_tick() for db_tick in s]
        return data

    def save_bar_data(self, datas: Sequence[Bar]):
        ds = [self.class_bar.from_bar(i) for i in datas]
        self.class_bar.save_all(ds)

    def save_tick_data(self, datas: Sequence[Tick]):
        ds = [self.class_tick.from_tick(i) for i in datas]
        self.class_tick.save_all(ds)


def init():
    db = SqliteDatabase(PATH)
    bar,tick = init_models(db)
    _database_manager = SqlManager(bar,tick)
    return _database_manager


database_manager = init()
