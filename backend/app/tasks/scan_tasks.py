from app.core.celery_app import celery_app
from app.services.scan_service import run_scan_job


@celery_app.task(name="run_scan_job", bind=True, max_retries=0)
def run_scan_task(self, scan_id: str):
    run_scan_job(scan_id)
    