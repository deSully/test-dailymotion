import logging
import sys
from typing import Final

LOG_FORMAT: Final[str] = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
