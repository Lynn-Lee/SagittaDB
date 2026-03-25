"""archive 任务（Sprint 3/4/5 实现）。"""
from app.celery_app import celery_app


@celery_app.task(bind=True, queue="default")
def placeholder_task(self, *args, **kwargs):
    return {"task": "archive", "status": "Sprint 实现中"}
