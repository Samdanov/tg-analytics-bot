import logging
from typing import Optional

from app.core.config import config


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure root logger once. Safe to call multiple times.
    """
    level_name = (level or config.log_level or "INFO").upper()
    level_value = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level_value,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
