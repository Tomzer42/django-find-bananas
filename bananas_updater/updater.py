from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from bananas_updater import create_bananas, reset_session_variables

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(create_bananas.bananas_of_the_day, 'cron', hour='10,22')
    scheduler.start()

def start_sessions(request):
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_session_variables.reset_session_variables, 'cron', hour='10,22', args=[request])
    scheduler.start()
