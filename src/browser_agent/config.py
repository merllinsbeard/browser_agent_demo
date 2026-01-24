"""
Configuration and Logging Setup

Provides centralized configuration and logging for the browser automation agent.
Reads LOG_LEVEL from environment variables for configurable logging.

Usage:
    from browser_agent.config import configure_logging, get_logger

    # Configure at application startup
    configure_logging()

    # Get logger in any module
    logger = get_logger(__name__)
"""

import logging
import os
import sys
from typing import Optional

# Default configuration
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)s: %(message)s"

# Valid log levels
VALID_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def get_log_level() -> int:
    """
    Get the log level from LOG_LEVEL environment variable.

    Returns:
        Logging level constant (e.g., logging.INFO)

    Supported values:
        DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    level_str = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    if level_str not in VALID_LEVELS:
        # Warn about invalid level and use default
        print(
            f"Warning: Invalid LOG_LEVEL '{level_str}'. "
            f"Valid values: {', '.join(VALID_LEVELS.keys())}. "
            f"Using {DEFAULT_LOG_LEVEL}.",
            file=sys.stderr,
        )
        return VALID_LEVELS[DEFAULT_LOG_LEVEL]

    return VALID_LEVELS[level_str]


def configure_logging(
    level: Optional[int] = None,
    verbose: bool = False,
) -> None:
    """
    Configure logging for the browser automation agent.

    Should be called once at application startup, before other modules
    import their loggers.

    Args:
        level: Override log level (default: from LOG_LEVEL env var)
        verbose: Use detailed format with timestamps (default: simple format)

    Environment Variables:
        LOG_LEVEL: Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL

    Example:
        # In main.py
        from browser_agent.config import configure_logging
        configure_logging()  # Uses LOG_LEVEL env var

        # For development
        configure_logging(level=logging.DEBUG, verbose=True)
    """
    if level is None:
        level = get_log_level()

    log_format = LOG_FORMAT if verbose else LOG_FORMAT_SIMPLE

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )

    # Set browser_agent logger specifically
    browser_agent_logger = logging.getLogger("browser_agent")
    browser_agent_logger.setLevel(level)

    # Quiet noisy third-party loggers in non-debug mode
    if level > logging.DEBUG:
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        from browser_agent.config import get_logger
        logger = get_logger(__name__)
        logger.debug("Debug message")
    """
    return logging.getLogger(name)
