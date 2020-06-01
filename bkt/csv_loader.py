import csv
from typing import TextIO
from datetime import datetime
from bkt.base import Bar
from bkt.database import database_manager
"""
author:Bohr
Load data from a csv file into database

Sample csv file:
"datetime","open","high","low","close","volume","multiplier","open_interest"
2010-4-16 09:15:00 3000.0 2990.0 3010.0 3000.0 1543215 1 0
2010-4-16 09:16:00 3001.0 2991.0 3011.0 3000.0 2135482 1 0
2010-4-16 09:17:00 3002.0 2992.0 3012.0 3000.0 1865462 1 0
2010-4-16 09:18:00 3003.0 2993.0 3013.0 3000.0 1962141 1 0
2010-4-16 09:19:00 3004.0 2994.0 3014.0 3000.0 3214121 1 0
2010-4-16 09:20:00 3005.0 2995.0 3015.0 3000.0 2121242 1 0
"""


def save_to_db(file:TextIO,
               vt_symbol: str,
               datetime_header: str,
               open_header: str,
               high_header: str,
               low_header: str,
               close_header: str,
               volume_header: str,
               datetime_format: str,
               multipiler: int=1):
    """
    datetime format example: %Y-%m-%d %H:%M
    """
    buf = [line.replace('\0',"") for line in file]
    reader = csv.DictReader(buf,delimiter=',')

    bars = []
    start = None
    count = 0
    for item in reader:
        if datetime_format:
            dt = datetime.strptime(item[datetime_header], datetime_format)
        else:
            dt = datetime.fromisoformat(item[datetime_header])

        bar = Bar(time=dt,
                  vt_symbol=vt_symbol,
                  open=item[open_header],
                  open_interest=0,
                  high=item[high_header],
                  low=item[low_header],
                  close=item[close_header],
                  volume=item[volume_header],
                  multiplier=multipiler)

        bars.append(bar)

        count += 1
        if not start:
            start = bar.datetime

    end = bar.datetime
    database_manager.save_bar_data(bars)
    return start, end, count






