"""Structured logging for OLX Monitor"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import deque


class MemoryHandler(logging.Handler):
    """Handler that stores log records in memory for UI display"""

    def __init__(self, max_records: int = 100):
        super().__init__()
        self.records: deque = deque(maxlen=max_records)

    def emit(self, record: logging.LogRecord):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname.lower(),
            "message": self.format(record),
            "logger": record.name,
        }
        self.records.appendleft(log_entry)

    def get_logs(self) -> list[dict]:
        """Get all stored log entries"""
        return list(self.records)

    def clear(self):
        """Clear all stored log entries"""
        self.records.clear()


# Global memory handler for UI access
_memory_handler: Optional[MemoryHandler] = None


def setup_logger(
    name: str = "olx_monitor",
    level: int = logging.DEBUG,
    log_file: Optional[Path] = None,
    max_memory_records: int = 100
) -> logging.Logger:
    """
    Setup structured logger with console, memory, and optional file output.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        max_memory_records: Maximum records to keep in memory

    Returns:
        Configured logger instance
    """
    global _memory_handler

    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Format with timestamp and context
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Memory handler for UI
    _memory_handler = MemoryHandler(max_records=max_memory_records)
    _memory_handler.setLevel(level)
    _memory_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_memory_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "olx_monitor") -> logging.Logger:
    """Get or create a logger instance"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_logger(name)
    # Evita duplicação: não propagar para loggers pai
    logger.propagate = False
    return logger


def get_memory_logs() -> list[dict]:
    """Get logs stored in memory for UI display"""
    if _memory_handler:
        return _memory_handler.get_logs()
    return []


def clear_memory_logs():
    """Clear logs stored in memory"""
    if _memory_handler:
        _memory_handler.clear()


# Create default logger on module import
logger = setup_logger()
