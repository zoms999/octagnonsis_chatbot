"""
ETL error handling utilities: classification and recovery policies
"""

from enum import Enum
from typing import Tuple


class ErrorType(str, Enum):
    VALIDATION = "validation_error"
    NETWORK = "network_error"
    DATABASE = "database_error"
    EXTERNAL_API = "external_api_error"
    TIMEOUT = "timeout_error"
    UNKNOWN = "unknown_error"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


def classify_error(error: Exception) -> Tuple[ErrorType, Severity, bool]:
    """Classify error and determine retryability.

    Returns: (error_type, severity, is_retryable)
    """
    message = str(error).lower()

    # Timeouts
    if any(k in message for k in ["timeout", "timed out", "deadline"]):
        return (ErrorType.TIMEOUT, Severity.WARNING, True)

    # Network
    if any(k in message for k in ["connection", "network", "dns", "socket"]):
        return (ErrorType.NETWORK, Severity.WARNING, True)

    # Database
    if any(k in message for k in ["database", "db", "sqlalchemy", "deadlock", "connection pool"]):
        return (ErrorType.DATABASE, Severity.CRITICAL, True)

    # External API
    if any(k in message for k in ["api", "rate limit", "quota", "service unavailable", "429", "503"]):
        return (ErrorType.EXTERNAL_API, Severity.WARNING, True)

    # Validation
    if any(k in message for k in ["validation", "invalid", "missing required", "schema"]):
        return (ErrorType.VALIDATION, Severity.INFO, False)

    return (ErrorType.UNKNOWN, Severity.WARNING, False)


