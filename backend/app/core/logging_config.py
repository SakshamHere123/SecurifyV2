import logging
import sys
from contextvars import ContextVar

# Holds the scan_id for whatever scan is currently being processed in THIS
# worker process. Set once at the top of run_scan_job; every log call made
# by any function further down the call stack -- parser, checkov, the
# agents, the controller -- automatically gets tagged with it via the
# filter below, without threading a scan_id parameter through every single
# function signature in the pipeline.
current_scan_id: ContextVar[str] = ContextVar("current_scan_id", default="-")


class ScanIdFilter(logging.Filter):
    def filter(self, record):
        record.scan_id = current_scan_id.get()
        return True


def configure_logging():
    """Call once per process (FastAPI startup, and Celery worker startup --
    they're separate processes, each needs this). Idempotent: calling it
    twice (e.g. on a dev reload) just skips re-adding handlers instead of
    duplicating every log line.
    """
    root = logging.getLogger()
    if getattr(root, "_securify_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ScanIdFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | scan=%(scan_id)s | %(name)s | %(message)s"
    ))

    root.handlers = [handler]
    root.setLevel(logging.INFO)
    root._securify_configured = True
