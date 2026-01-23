from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from rss_analyzer import run_rss_auto_analysis

scheduler = BackgroundScheduler()

def start_scheduler():
    loop = asyncio.get_event_loop()

    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(
            run_rss_auto_analysis(), loop
        ),
        trigger="interval",
        minutes=2,  # zum Testen
        id="rss_job",
        replace_existing=True,
    )

    scheduler.start()
    print("RSS SCHEDULER STARTED")
