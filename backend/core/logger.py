import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Callable

LOG_DIR = Path(os.getenv("LOG_DIR", Path(__file__).parent.parent.parent / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 终端输出
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)

        # 文件输出（按日期滚动）
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            LOG_DIR / f"app-{today}.log", encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

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
