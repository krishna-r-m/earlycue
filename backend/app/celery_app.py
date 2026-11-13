from celery import Celery
from celery.signals import worker_ready
from . import config

celery=Celery("marketpulse",broker=config.redis_url,backend=config.redis_url,include=["app.tasks"])
celery.conf.update(
    timezone="Asia/Kolkata",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=1800,
    broker_connection_retry_on_startup=True,
    task_publish_retry_policy={"max_retries":1,"interval_start":0,"interval_step":0.2,"interval_max":0.5},
    beat_schedule={
        "refresh-news":{
            "task":"app.tasks.refresh_news",
            "schedule":config.fetch_interval_minutes*60,
            "options":{"expires":config.fetch_interval_minutes*60},
        },
        "sync-instruments":{
            "task":"app.tasks.sync_instruments",
            "schedule":7*24*3600,
        },
        **({"deep-crawl":{
            "task":"app.tasks.deep_crawl",
            "schedule":config.crawl_interval_minutes*60,
            "options":{"expires":config.crawl_interval_minutes*60},
        }} if config.deep_crawl else {}),
    },
)

@worker_ready.connect
def fetch_on_start(**kwargs):
    celery.send_task("app.tasks.sync_instruments")
    celery.send_task("app.tasks.refresh_news")
    if config.deep_crawl:
        celery.send_task("app.tasks.deep_crawl")
