import os
import time
from app import app, db, ensure_database
from collector import sync_all

if __name__=='__main__':
    with app.app_context():ensure_database()
    interval=max(60,int(os.getenv('SYNC_SECONDS','300')))
    while True:
        start=time.monotonic()
        try:
            for result in sync_all(): print(result,flush=True)
        except Exception as e:
            print('同步程序錯誤，下一輪會重試：'+type(e).__name__,flush=True)
        if os.getenv('SYNC_ONCE')=='1':break
        time.sleep(max(1,interval-(time.monotonic()-start)))
