from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.sincronizar_todas_entregas import sincronizar_todas_entregas

def iniciar_agendador(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: sincronizar_todas_entregas(), trigger='cron', hour=23, minute=0)
    scheduler.start()
    app.scheduler = scheduler