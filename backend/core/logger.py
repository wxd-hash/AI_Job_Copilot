import logging
import json
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Callable


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_agent_execution(agent_name: str) -> Callable:
    """Decorator to log agent execution with timing and structured output."""

    def decorator(func: Callable) -> Callable:
        logger = setup_logger(f"agent.{agent_name}")

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            logger.info(f"▶ {agent_name} started")
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"✓ {agent_name} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"✗ {agent_name} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    return decorator
