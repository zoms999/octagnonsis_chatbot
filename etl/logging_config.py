"""
ETL Logging Configuration
Comprehensive logging setup for ETL processing pipeline
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import structlog

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class ETLFormatter(logging.Formatter):
    """Custom formatter for ETL logs with structured data"""
    
    def __init__(self):
        super().__init__()
        self.hostname = os.getenv('HOSTNAME', 'localhost')
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'hostname': self.hostname,
            'process_id': os.getpid(),
            'thread_id': record.thread,
        }
        
        # Add extra fields if present
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'stage'):
            log_entry['stage'] = record.stage
        
        if hasattr(record, 'duration'):
            log_entry['duration_seconds'] = record.duration
        
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add file and line info for debug level
        if record.levelno <= logging.DEBUG:
            log_entry['file'] = record.filename
            log_entry['line'] = record.lineno
            log_entry['function'] = record.funcName
        
        return json.dumps(log_entry, ensure_ascii=False)

class ETLLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds ETL context to log records"""
    
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        # Add extra context to log record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        return msg, kwargs

def setup_etl_logging(
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    enable_structured_logging: bool = True,
    log_rotation_size: int = 10 * 1024 * 1024,  # 10MB
    log_retention_count: int = 5
) -> None:
    """
    Setup comprehensive logging for ETL pipeline
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to log to files
        enable_console_logging: Whether to log to console
        enable_structured_logging: Whether to use structured JSON logging
        log_rotation_size: Size in bytes for log rotation
        log_retention_count: Number of rotated log files to keep
    """
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Setup formatters
    if enable_structured_logging:
        formatter = ETLFormatter()
    else:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        )
    
    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file_logging:
        # Main ETL log file
        etl_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "etl_processing.log",
            maxBytes=log_rotation_size,
            backupCount=log_retention_count
        )
        etl_handler.setLevel(numeric_level)
        etl_handler.setFormatter(formatter)
        root_logger.addHandler(etl_handler)
        
        # Error-only log file
        error_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "etl_errors.log",
            maxBytes=log_rotation_size,
            backupCount=log_retention_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log file (for timing and metrics)
        perf_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "etl_performance.log",
            maxBytes=log_rotation_size,
            backupCount=log_retention_count
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(formatter)
        
        # Add filter to only log performance-related messages
        perf_handler.addFilter(lambda record: hasattr(record, 'duration') or 'performance' in record.getMessage().lower())
        root_logger.addHandler(perf_handler)
    
    # Configure specific loggers
    configure_etl_loggers(numeric_level)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"ETL logging configured: level={log_level}, "
        f"file_logging={enable_file_logging}, "
        f"console_logging={enable_console_logging}, "
        f"structured_logging={enable_structured_logging}"
    )

def setup_logging(
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    enable_structured_logging: bool = True,
    log_rotation_size: int = 10 * 1024 * 1024,
    log_retention_count: int = 5,
) -> None:
    """Backward-compatible alias used by main.py."""
    setup_etl_logging(
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        enable_console_logging=enable_console_logging,
        enable_structured_logging=enable_structured_logging,
        log_rotation_size=log_rotation_size,
        log_retention_count=log_retention_count,
    )

def configure_etl_loggers(log_level: int) -> None:
    """Configure specific loggers for ETL components"""
    
    # ETL component loggers
    etl_loggers = [
        'etl.orchestrator',
        'etl.tasks',
        'etl.test_completion_handler',
        'etl.legacy_query_executor',
        'etl.document_transformer',
        'etl.vector_embedder',
        'database.repositories',
        'database.vector_search',
        'rag.context_builder',
        'rag.question_processor',
        'rag.response_generator'
    ]
    
    for logger_name in etl_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    
    # Set specific levels for noisy libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
    # Note: Celery and Redis logging removed - using database-based job tracking

def get_etl_logger(
    name: str,
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    stage: Optional[str] = None
) -> ETLLoggerAdapter:
    """
    Get ETL logger with context
    
    Args:
        name: Logger name
        job_id: Job identifier for context
        user_id: User identifier for context
        stage: Processing stage for context
        
    Returns:
        Logger adapter with ETL context
    """
    
    logger = logging.getLogger(name)
    
    # Build context
    context = {}
    if job_id:
        context['job_id'] = job_id
    if user_id:
        context['user_id'] = user_id
    if stage:
        context['stage'] = stage
    
    return ETLLoggerAdapter(logger, context)

class ETLLogContext:
    """Context manager for ETL logging with automatic timing"""
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stage: Optional[str] = None,
        log_level: int = logging.INFO
    ):
        self.logger = logger
        self.operation = operation
        self.job_id = job_id
        self.user_id = user_id
        self.stage = stage
        self.log_level = log_level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        
        # Log operation start
        extra = {}
        if self.job_id:
            extra['job_id'] = self.job_id
        if self.user_id:
            extra['user_id'] = self.user_id
        if self.stage:
            extra['stage'] = self.stage
        
        self.logger.log(
            self.log_level,
            f"Starting {self.operation}",
            extra=extra
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Prepare extra context
        extra = {
            'duration': duration,
            'operation': self.operation
        }
        if self.job_id:
            extra['job_id'] = self.job_id
        if self.user_id:
            extra['user_id'] = self.user_id
        if self.stage:
            extra['stage'] = self.stage
        
        if exc_type is None:
            # Success
            self.logger.log(
                self.log_level,
                f"Completed {self.operation} in {duration:.2f}s",
                extra=extra
            )
        else:
            # Error
            extra['error_type'] = exc_type.__name__
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                extra=extra,
                exc_info=(exc_type, exc_val, exc_tb)
            )

def log_etl_metrics(
    logger: logging.Logger,
    metrics: Dict[str, Any],
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    stage: Optional[str] = None
) -> None:
    """
    Log ETL performance metrics
    
    Args:
        logger: Logger instance
        metrics: Dictionary of metrics to log
        job_id: Job identifier for context
        user_id: User identifier for context
        stage: Processing stage for context
    """
    
    extra = {
        'metrics': metrics,
        'metric_type': 'performance'
    }
    
    if job_id:
        extra['job_id'] = job_id
    if user_id:
        extra['user_id'] = user_id
    if stage:
        extra['stage'] = stage
    
    logger.info(
        f"ETL Metrics: {json.dumps(metrics, default=str)}",
        extra=extra
    )

def log_etl_checkpoint(
    logger: logging.Logger,
    checkpoint_data: Dict[str, Any],
    job_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log ETL checkpoint data
    
    Args:
        logger: Logger instance
        checkpoint_data: Checkpoint data to log
        job_id: Job identifier for context
        user_id: User identifier for context
    """
    
    extra = {
        'checkpoint': checkpoint_data,
        'log_type': 'checkpoint'
    }
    
    if job_id:
        extra['job_id'] = job_id
    if user_id:
        extra['user_id'] = user_id
    
    logger.info(
        f"ETL Checkpoint: {checkpoint_data.get('stage', 'unknown')}",
        extra=extra
    )

# Setup structured logging with structlog (optional enhancement)
def setup_structured_logging():
    """Setup structlog for enhanced structured logging"""
    try:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        return True
    except ImportError:
        # structlog not available, use standard logging
        return False

# Initialize logging on module import
if __name__ != '__main__':
    # Setup logging with environment-based configuration
    log_level = os.getenv('ETL_LOG_LEVEL', 'INFO')
    enable_file_logging = os.getenv('ETL_ENABLE_FILE_LOGGING', 'true').lower() == 'true'
    enable_console_logging = os.getenv('ETL_ENABLE_CONSOLE_LOGGING', 'true').lower() == 'true'
    enable_structured_logging = os.getenv('ETL_ENABLE_STRUCTURED_LOGGING', 'true').lower() == 'true'
    
    setup_etl_logging(
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        enable_console_logging=enable_console_logging,
        enable_structured_logging=enable_structured_logging
    )

# Example usage functions
def example_usage():
    """Example of how to use ETL logging"""
    
    # Basic logger
    logger = logging.getLogger(__name__)
    logger.info("Basic log message")
    
    # Logger with context
    etl_logger = get_etl_logger(
        __name__,
        job_id="job_123",
        user_id="user_456",
        stage="document_transformation"
    )
    etl_logger.info("ETL operation with context")
    
    # Using context manager for timing
    with ETLLogContext(logger, "document processing", job_id="job_123"):
        # Simulate work
        import time
        time.sleep(0.1)
    
    # Log metrics
    log_etl_metrics(
        logger,
        {
            "documents_processed": 5,
            "processing_time_seconds": 12.5,
            "memory_usage_mb": 256.7
        },
        job_id="job_123"
    )

if __name__ == '__main__':
    # Test logging configuration
    setup_etl_logging(log_level="DEBUG")
    example_usage()