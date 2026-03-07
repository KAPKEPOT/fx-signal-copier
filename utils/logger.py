# fx/utils/logger.py
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional
import json
from datetime import datetime

from config.settings import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: blue,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }
    
    def format(self, record):
        color = self.FORMATS.get(record.levelno, self.grey)
        formatter = logging.Formatter(
            f"{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{self.reset}",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return formatter.format(record)


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get logger
    logger = logging.getLogger(name or __name__)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.LOG_FILE:
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            settings.LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)
    
    # JSON log file for structured logging (optional)
    json_handler = TimedRotatingFileHandler(
        log_dir / "structured.log",
        when="midnight",
        interval=1,
        backupCount=7
    )
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(logging.INFO)
    logger.addHandler(json_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_error(self, message: str, exc_info: bool = True):
        """Log error with context"""
        self.logger.error(message, exc_info=exc_info)
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def log_debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)