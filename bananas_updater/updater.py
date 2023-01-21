from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from bananas_updater import create_bananas

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(create_bananas.bananas_of_the_day, 'interval', minutes=1)
    scheduler.start()
