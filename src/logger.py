"""Logging configuration with rotation support."""
import logging
import logging.handlers
import os
from pathlib import Path
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with both console and file handlers with rotation."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create log directory if it doesn't exist
    log_dir = Path(settings.log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Console handler with simple format
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with JSON format and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.log_file_path,
        maxBytes=settings.log_max_size * 1024 * 1024,  # Convert MB to bytes
        backupCount=settings.log_backup_count
    )
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    return setup_logger(name)


# Create loggers for different components
main_logger = get_logger("docker_monitor.main")
ssh_logger = get_logger("docker_monitor.ssh")
docker_logger = get_logger("docker_monitor.docker")
caddy_logger = get_logger("docker_monitor.caddy")
api_logger = get_logger("docker_monitor.api")