"""Worker configuration and startup."""
import logging
from src.workers.tasks import celery_app

logger = logging.getLogger(__name__)


def start_worker(loglevel: str = "info", concurrency: int = 4):
    """Start Celery worker.
    
    Args:
        loglevel: Log level
        concurrency: Number of concurrent workers
    """
    logger.info(f"Starting Celery worker with {concurrency} workers")
    
    celery_app.worker_main([
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        "--prefetch-multiplier=4",
        "--max-tasks-per-child=1000",
    ])


if __name__ == "__main__":
    start_worker(loglevel="info", concurrency=4)
