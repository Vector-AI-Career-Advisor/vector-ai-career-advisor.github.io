"""Centralized logging configuration."""
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


def setup_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # delay=True: file is only created on first write (when an error triggers a flush)
    file_handler = logging.FileHandler(log_path, delay=True)
    file_handler.setFormatter(fmt)

    # flushOnClose=False: discard buffer on clean shutdown instead of writing to file
    memory_handler = logging.handlers.MemoryHandler(
        capacity=1000,
        flushLevel=logging.ERROR,
        target=file_handler,
        flushOnClose=False,
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(memory_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
