"""Logging configuration using Loguru."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip"
) -> None:
    """
    Configure Loguru logging with console and file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (defaults to logs/app_{time}.log)
        rotation: Log rotation policy
        retention: Log retention period
        compression: Compression format for rotated logs
    """
    # Remove default handler
    logger.remove()

    # Determine log level
    level = log_level or settings.log_level

    # Console logging with colors
    if settings.log_format == "json":
        # JSON format for production
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            serialize=True,
            backtrace=True,
            diagnose=settings.debug
        )
    else:
        # Human-readable format for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=settings.debug
        )

    # File logging with rotation
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    if log_file is None:
        log_file = str(log_dir / "app_{time:YYYY-MM-DD}.log")

    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        serialize=settings.log_format == "json",
        backtrace=True,
        diagnose=settings.debug
    )

    logger.info(f"Logging configured: level={level}, format={settings.log_format}")


def get_logger(name: str):
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Initialize logging on import
setup_logging()
