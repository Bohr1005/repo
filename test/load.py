from bkt.func import load_bar_data
from datetime import datetime


pool = ('IH','if')
bar_dict = load_bar_data(pool=pool,
                         start=datetime(2017,1,1),
                         end=datetime(2019,1,1))

print(bar_dict.items())