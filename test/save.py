import os
from bkt.csv_loader import save_to_db
os.chdir(r"C:\Users\dell\Desktop\股指期货数据")

for file in os.listdir():
    with open(file) as f:
        save_to_db(f,
                   vt_symbol=file[:-4],
                   datetime_header='datetime',
                   open_header='open',
                   high_header='high',
                   low_header='low',
                   close_header='close',
                   volume_header='volume',
                   datetime_format='%Y-%m-%d %H:%M:%S',
                   multipiler=300)
        print(f"finished:{file}")

