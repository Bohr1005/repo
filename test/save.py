import os
from bkt.csv_loader import save_to_db
os.chdir(r"C:\Users\dell\Desktop\股指期货数据")

for file in os.listdir():
    with open(file) as f:
        save_to_db(f,
                   vt_symbol=file[:-4],
                   datetime_header='Datetime',
                   open_header='Open',
                   high_header='High',
                   low_header='Low',
                   close_header='Close',
                   volume_header='Volume',
                   datetime_format='%Y/%m/%d %H:%M')

