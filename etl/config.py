"""
ETL Configuration
Configuration settings for ETL processing without external dependencies
"""

import os

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost/aptitude_chatbot')

# Google API configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Background processing configuration (asyncio-based)
BACKGROUND_PROCESSING_CONFIG = {
    'max_concurrent_jobs': int(os.getenv('ETL_MAX_CONCURRENT_JOBS', '5')),
    'job_timeout_minutes': int(os.getenv('ETL_JOB_TIMEOUT_MINUTES', '30')),
    'max_retries': int(os.getenv('ETL_MAX_RETRIES', '3')),
    'retry_delay_seconds': int(os.getenv('ETL_RETRY_DELAY_SECONDS', '60')),
    'enable_job_tracking': os.getenv('ETL_ENABLE_JOB_TRACKING', 'true').lower() == 'true',
    'job_tracking_ttl_days': int(os.getenv('ETL_JOB_TRACKING_TTL_DAYS', '7')),
    'enable_admin_notifications': os.getenv('ETL_ENABLE_ADMIN_NOTIFICATIONS', 'true').lower() == 'true',
    'notification_channels': os.getenv('ETL_NOTIFICATION_CHANNELS', 'log,email').split(','),
    'worker_pool_size': int(os.getenv('ETL_WORKER_POOL_SIZE', '4')),
    'job_cleanup_interval_hours': int(os.getenv('ETL_JOB_CLEANUP_INTERVAL_HOURS', '24')),
    'health_check_interval_minutes': int(os.getenv('ETL_HEALTH_CHECK_INTERVAL_MINUTES', '5')),
    'enable_partial_completion': os.getenv('ETL_ENABLE_PARTIAL_COMPLETION', 'true').lower() == 'true',
}

# ETL processing configuration
ETL_CONFIG = {
    'max_concurrent_jobs': int(os.getenv('ETL_MAX_CONCURRENT_JOBS', '5')),
    'job_timeout_minutes': int(os.getenv('ETL_JOB_TIMEOUT_MINUTES', '30')),
    'max_retries': int(os.getenv('ETL_MAX_RETRIES', '3')),
    'retry_delay_seconds': int(os.getenv('ETL_RETRY_DELAY_SECONDS', '60')),
    'enable_job_tracking': os.getenv('ETL_ENABLE_JOB_TRACKING', 'true').lower() == 'true',
    'job_tracking_ttl_days': int(os.getenv('ETL_JOB_TRACKING_TTL_DAYS', '7')),
    'enable_admin_notifications': os.getenv('ETL_ENABLE_ADMIN_NOTIFICATIONS', 'true').lower() == 'true',
    'notification_channels': os.getenv('ETL_NOTIFICATION_CHANNELS', 'log,email').split(','),
    'enable_partial_completion': os.getenv('ETL_ENABLE_PARTIAL_COMPLETION', 'true').lower() == 'true',
}

# Vector embedding configuration
EMBEDDING_CONFIG = {
    'batch_size': int(os.getenv('EMBEDDING_BATCH_SIZE', '5')),
    'max_retries': int(os.getenv('EMBEDDING_MAX_RETRIES', '3')),
    'retry_delay': float(os.getenv('EMBEDDING_RETRY_DELAY', '1.0')),
    'rate_limit_per_minute': int(os.getenv('EMBEDDING_RATE_LIMIT_PER_MINUTE', '60')),
    'enable_cache': os.getenv('EMBEDDING_ENABLE_CACHE', 'true').lower() == 'true',
    'cache_ttl_hours': int(os.getenv('EMBEDDING_CACHE_TTL_HOURS', '24')),
}

# Query execution configuration
QUERY_CONFIG = {
    'max_retries': int(os.getenv('QUERY_MAX_RETRIES', '3')),
    'retry_delay': float(os.getenv('QUERY_RETRY_DELAY', '1.0')),
    'max_workers': int(os.getenv('QUERY_MAX_WORKERS', '4')),
    'timeout_seconds': int(os.getenv('QUERY_TIMEOUT_SECONDS', '300')),
}

# Document transformation configuration
DOCUMENT_CONFIG = {
    'enable_validation': os.getenv('DOCUMENT_ENABLE_VALIDATION', 'true').lower() == 'true',
    'max_summary_length': int(os.getenv('DOCUMENT_MAX_SUMMARY_LENGTH', '1000')),
    'enable_metadata': os.getenv('DOCUMENT_ENABLE_METADATA', 'true').lower() == 'true',
}

# Monitoring and alerting configuration
MONITORING_CONFIG = {
    'enable_metrics': os.getenv('MONITORING_ENABLE_METRICS', 'true').lower() == 'true',
    'metrics_interval_seconds': int(os.getenv('MONITORING_METRICS_INTERVAL_SECONDS', '60')),
    'alert_on_failure': os.getenv('MONITORING_ALERT_ON_FAILURE', 'true').lower() == 'true',
    'alert_threshold_failures': int(os.getenv('MONITORING_ALERT_THRESHOLD_FAILURES', '3')),
    'alert_threshold_time_minutes': int(os.getenv('MONITORING_ALERT_THRESHOLD_TIME_MINUTES', '60')),
}

# Environment-specific configuration
if os.getenv('ENVIRONMENT') == 'development':
    # Development settings for faster testing
    ETL_CONFIG['max_concurrent_jobs'] = 2
    ETL_CONFIG['job_timeout_minutes'] = 5
    BACKGROUND_PROCESSING_CONFIG['max_concurrent_jobs'] = 2
    BACKGROUND_PROCESSING_CONFIG['job_timeout_minutes'] = 5

if os.getenv('ENVIRONMENT') == 'production':
    # Production optimizations
    ETL_CONFIG['max_concurrent_jobs'] = 10
    ETL_CONFIG['job_timeout_minutes'] = 60
    BACKGROUND_PROCESSING_CONFIG['max_concurrent_jobs'] = 10
    BACKGROUND_PROCESSING_CONFIG['job_timeout_minutes'] = 60