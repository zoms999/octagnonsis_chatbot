"""
Preference Query Performance Optimizer
Provides connection pooling, query caching, timeout handling, and performance monitoring
for preference-related database queries.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager
import hashlib
import json
import threading
from collections import defaultdict
import weakref

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError, TimeoutError as SQLTimeoutError
from sqlalchemy.pool import QueuePool, StaticPool
import structlog

# Setup structured logging
logger = logging.getLogger(__name__)
perf_logger = structlog.get_logger("preference_query_performance")

@dataclass
class QueryCacheEntry:
    """Cache entry for query results"""
    result: List[Dict[str, Any]]
    timestamp: datetime
    execution_time: float
    hit_count: int = 0
    
    def is_expired(self, ttl_seconds: int = 300) -> bool:
        """Check if cache entry is expired (default 5 minutes)"""
        return (datetime.now() - self.timestamp).total_seconds() > ttl_seconds

@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for a specific query"""
    query_name: str
    total_executions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    timeout_count: int = 0
    error_count: int = 0
    last_execution: Optional[datetime] = None
    
    @property
    def avg_execution_time(self) -> float:
        """Average execution time in seconds"""
        if self.total_executions == 0:
            return 0.0
        return self.total_execution_time / self.total_executions
    
    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage"""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100

@dataclass
class ConnectionPoolMetrics:
    """Metrics for database connection pool"""
    pool_size: int = 0
    checked_out: int = 0
    overflow: int = 0
    checked_in: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    pool_timeouts: int = 0
    
    @property
    def utilization_rate(self) -> float:
        """Connection pool utilization rate as percentage"""
        if self.pool_size == 0:
            return 0.0
        return (self.checked_out / self.pool_size) * 100

class PreferenceQueryOptimizer:
    """
    Optimized query executor for preference queries with connection pooling,
    caching, timeout handling, and performance monitoring.
    """
    
    def __init__(
        self,
        connection_string: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        query_timeout: int = 30,
        cache_ttl: int = 300,
        enable_cache: bool = True
    ):
        self.connection_string = connection_string
        self.query_timeout = query_timeout
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        
        # Initialize connection pool with optimized settings
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Detect stale connections
            echo=False,
            connect_args={
                "connect_timeout": 10,
                "options": f"-c statement_timeout={query_timeout * 1000}ms -c lock_timeout=10s -c idle_in_transaction_session_timeout=30s"
            }
        )
        
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Query cache and metrics
        self._query_cache: Dict[str, QueryCacheEntry] = {}
        self._cache_lock = threading.RLock()
        self._metrics: Dict[str, QueryPerformanceMetrics] = {}
        self._metrics_lock = threading.RLock()
        
        # Thread pool for query execution
        self._executor = ThreadPoolExecutor(
            max_workers=min(32, (pool_size + max_overflow) * 2),
            thread_name_prefix="preference_query"
        )
        
        # Connection pool monitoring
        self._pool_metrics = ConnectionPoolMetrics()
        
        perf_logger.info(
            "Preference query optimizer initialized",
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            query_timeout=query_timeout,
            cache_enabled=enable_cache,
            cache_ttl=cache_ttl
        )
    
    def _generate_cache_key(self, query_name: str, anp_seq: int, sql: str) -> str:
        """Generate cache key for query"""
        key_data = f"{query_name}:{anp_seq}:{sql}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result if available and not expired"""
        if not self.enable_cache:
            return None
        
        with self._cache_lock:
            entry = self._query_cache.get(cache_key)
            if entry and not entry.is_expired(self.cache_ttl):
                entry.hit_count += 1
                perf_logger.debug(
                    "Cache hit for preference query",
                    cache_key=cache_key,
                    hit_count=entry.hit_count,
                    age_seconds=(datetime.now() - entry.timestamp).total_seconds()
                )
                return entry.result
            elif entry:
                # Remove expired entry
                del self._query_cache[cache_key]
                perf_logger.debug(
                    "Cache entry expired and removed",
                    cache_key=cache_key,
                    age_seconds=(datetime.now() - entry.timestamp).total_seconds()
                )
        
        return None
    
    def _cache_result(
        self, 
        cache_key: str, 
        result: List[Dict[str, Any]], 
        execution_time: float
    ) -> None:
        """Cache query result"""
        if not self.enable_cache:
            return
        
        with self._cache_lock:
            self._query_cache[cache_key] = QueryCacheEntry(
                result=result,
                timestamp=datetime.now(),
                execution_time=execution_time
            )
            
            # Limit cache size to prevent memory issues
            if len(self._query_cache) > 1000:
                # Remove oldest entries
                sorted_entries = sorted(
                    self._query_cache.items(),
                    key=lambda x: x[1].timestamp
                )
                for key, _ in sorted_entries[:100]:  # Remove oldest 100 entries
                    del self._query_cache[key]
                
                perf_logger.info(
                    "Cache size limit reached, removed oldest entries",
                    cache_size=len(self._query_cache)
                )
    
    def _update_metrics(
        self,
        query_name: str,
        execution_time: float,
        cache_hit: bool,
        timeout: bool = False,
        error: bool = False
    ) -> None:
        """Update performance metrics"""
        with self._metrics_lock:
            if query_name not in self._metrics:
                self._metrics[query_name] = QueryPerformanceMetrics(query_name=query_name)
            
            metrics = self._metrics[query_name]
            metrics.total_executions += 1
            metrics.last_execution = datetime.now()
            
            if cache_hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
                metrics.total_execution_time += execution_time
                metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
                metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
            
            if timeout:
                metrics.timeout_count += 1
            
            if error:
                metrics.error_count += 1
    
    def _update_pool_metrics(self) -> None:
        """Update connection pool metrics"""
        pool = self.engine.pool
        self._pool_metrics.pool_size = pool.size()
        self._pool_metrics.checked_out = pool.checkedout()
        self._pool_metrics.overflow = pool.overflow()
        self._pool_metrics.checked_in = pool.checkedin()
        self._pool_metrics.total_connections = self._pool_metrics.checked_out + self._pool_metrics.checked_in
    
    def _execute_query_sync(
        self, 
        sql: str, 
        params: Dict[str, Any],
        query_name: str
    ) -> List[Dict[str, Any]]:
        """Execute query synchronously with timeout handling"""
        session = None
        try:
            session = self.session_factory()
            
            # Set query timeout at session level
            session.execute(text(f"SET statement_timeout = '{self.query_timeout}s'"))
            
            start_time = time.time()
            result = session.execute(text(sql), params)
            rows = result.mappings().all()
            execution_time = time.time() - start_time
            
            # Convert to list of dicts
            result_data = [dict(row) for row in rows]
            
            perf_logger.debug(
                "Query executed successfully",
                query_name=query_name,
                execution_time=execution_time,
                row_count=len(result_data),
                anp_seq=params.get('anp_seq')
            )
            
            return result_data
            
        except (SQLTimeoutError, FutureTimeoutError) as e:
            perf_logger.warning(
                "Query timeout",
                query_name=query_name,
                timeout_seconds=self.query_timeout,
                anp_seq=params.get('anp_seq'),
                error=str(e)
            )
            raise TimeoutError(f"Query '{query_name}' timed out after {self.query_timeout}s")
            
        except (DisconnectionError, OperationalError) as e:
            perf_logger.error(
                "Database connection error",
                query_name=query_name,
                anp_seq=params.get('anp_seq'),
                error=str(e)
            )
            raise
            
        except Exception as e:
            perf_logger.error(
                "Query execution error",
                query_name=query_name,
                anp_seq=params.get('anp_seq'),
                error=str(e)
            )
            raise
            
        finally:
            if session:
                session.close()
    
    async def execute_preference_query(
        self,
        query_name: str,
        anp_seq: int,
        sql: str,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Execute preference query with optimization features:
        - Connection pooling
        - Query caching
        - Timeout handling
        - Performance monitoring
        - Retry logic with exponential backoff
        """
        cache_key = self._generate_cache_key(query_name, anp_seq, sql)
        params = {"anp_seq": anp_seq}
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            self._update_metrics(query_name, 0.0, cache_hit=True)
            return cached_result
        
        # Execute query with retries
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute query in thread pool with timeout
                future = self._executor.submit(
                    self._execute_query_sync,
                    sql,
                    params,
                    query_name
                )
                
                try:
                    result = await asyncio.wait_for(
                        asyncio.wrap_future(future),
                        timeout=self.query_timeout + 5  # Add buffer to asyncio timeout
                    )
                except asyncio.TimeoutError:
                    future.cancel()
                    raise TimeoutError(f"Query '{query_name}' timed out after {self.query_timeout}s")
                
                execution_time = time.time() - start_time
                
                # Cache successful result
                self._cache_result(cache_key, result, execution_time)
                
                # Update metrics
                self._update_metrics(query_name, execution_time, cache_hit=False)
                self._update_pool_metrics()
                
                perf_logger.info(
                    "Preference query completed successfully",
                    query_name=query_name,
                    anp_seq=anp_seq,
                    attempt=attempt + 1,
                    execution_time=execution_time,
                    row_count=len(result),
                    cache_hit=False
                )
                
                return result
                
            except TimeoutError as e:
                execution_time = time.time() - start_time
                self._update_metrics(query_name, execution_time, cache_hit=False, timeout=True)
                last_exception = e
                
                perf_logger.warning(
                    "Preference query timeout",
                    query_name=query_name,
                    anp_seq=anp_seq,
                    attempt=attempt + 1,
                    execution_time=execution_time,
                    will_retry=attempt < max_retries
                )
                
                if attempt < max_retries:
                    # Exponential backoff for timeouts
                    delay = min(2 ** attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
                    
            except (DisconnectionError, OperationalError) as e:
                execution_time = time.time() - start_time
                self._update_metrics(query_name, execution_time, cache_hit=False, error=True)
                last_exception = e
                
                perf_logger.warning(
                    "Preference query connection error",
                    query_name=query_name,
                    anp_seq=anp_seq,
                    attempt=attempt + 1,
                    execution_time=execution_time,
                    error=str(e),
                    will_retry=attempt < max_retries
                )
                
                if attempt < max_retries:
                    # Shorter delay for connection errors
                    delay = 1.0 * (attempt + 1)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self._update_metrics(query_name, execution_time, cache_hit=False, error=True)
                last_exception = e
                
                perf_logger.error(
                    "Preference query unexpected error",
                    query_name=query_name,
                    anp_seq=anp_seq,
                    attempt=attempt + 1,
                    execution_time=execution_time,
                    error=str(e),
                    will_retry=attempt < max_retries
                )
                
                if attempt < max_retries:
                    delay = 0.5 * (attempt + 1)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # All retries exhausted
        self._update_metrics(query_name, 0.0, cache_hit=False, error=True)
        
        perf_logger.error(
            "Preference query failed after all retries",
            query_name=query_name,
            anp_seq=anp_seq,
            total_attempts=max_retries + 1,
            final_error=str(last_exception) if last_exception else "Unknown error"
        )
        
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"Query '{query_name}' failed after all retries")
    
    def get_performance_metrics(self) -> Dict[str, QueryPerformanceMetrics]:
        """Get performance metrics for all queries"""
        with self._metrics_lock:
            return dict(self._metrics)
    
    def get_connection_pool_metrics(self) -> ConnectionPoolMetrics:
        """Get connection pool metrics"""
        self._update_pool_metrics()
        return self._pool_metrics
    
    def clear_cache(self) -> int:
        """Clear query cache and return number of entries removed"""
        with self._cache_lock:
            count = len(self._query_cache)
            self._query_cache.clear()
            perf_logger.info("Query cache cleared", entries_removed=count)
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._cache_lock:
            total_entries = len(self._query_cache)
            total_hits = sum(entry.hit_count for entry in self._query_cache.values())
            
            if self._query_cache:
                avg_age = sum(
                    (datetime.now() - entry.timestamp).total_seconds()
                    for entry in self._query_cache.values()
                ) / total_entries
                
                oldest_entry = min(
                    self._query_cache.values(),
                    key=lambda x: x.timestamp
                )
                newest_entry = max(
                    self._query_cache.values(),
                    key=lambda x: x.timestamp
                )
                
                oldest_age = (datetime.now() - oldest_entry.timestamp).total_seconds()
                newest_age = (datetime.now() - newest_entry.timestamp).total_seconds()
            else:
                avg_age = oldest_age = newest_age = 0
            
            return {
                "total_entries": total_entries,
                "total_hits": total_hits,
                "avg_age_seconds": avg_age,
                "oldest_age_seconds": oldest_age,
                "newest_age_seconds": newest_age,
                "cache_enabled": self.enable_cache,
                "cache_ttl": self.cache_ttl
            }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        metrics = self.get_performance_metrics()
        pool_metrics = self.get_connection_pool_metrics()
        cache_stats = self.get_cache_stats()
        
        # Calculate aggregate statistics
        total_executions = sum(m.total_executions for m in metrics.values())
        total_cache_hits = sum(m.cache_hits for m in metrics.values())
        total_cache_misses = sum(m.cache_misses for m in metrics.values())
        total_timeouts = sum(m.timeout_count for m in metrics.values())
        total_errors = sum(m.error_count for m in metrics.values())
        
        overall_cache_hit_rate = 0.0
        if total_cache_hits + total_cache_misses > 0:
            overall_cache_hit_rate = (total_cache_hits / (total_cache_hits + total_cache_misses)) * 100
        
        avg_execution_time = 0.0
        if metrics:
            avg_execution_time = sum(m.avg_execution_time for m in metrics.values()) / len(metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_stats": {
                "total_executions": total_executions,
                "total_cache_hits": total_cache_hits,
                "total_cache_misses": total_cache_misses,
                "overall_cache_hit_rate": overall_cache_hit_rate,
                "total_timeouts": total_timeouts,
                "total_errors": total_errors,
                "avg_execution_time": avg_execution_time
            },
            "query_metrics": {name: {
                "total_executions": m.total_executions,
                "cache_hit_rate": m.cache_hit_rate,
                "avg_execution_time": m.avg_execution_time,
                "min_execution_time": m.min_execution_time if m.min_execution_time != float('inf') else 0,
                "max_execution_time": m.max_execution_time,
                "timeout_count": m.timeout_count,
                "error_count": m.error_count,
                "last_execution": m.last_execution.isoformat() if m.last_execution else None
            } for name, m in metrics.items()},
            "connection_pool": {
                "pool_size": pool_metrics.pool_size,
                "checked_out": pool_metrics.checked_out,
                "overflow": pool_metrics.overflow,
                "utilization_rate": pool_metrics.utilization_rate,
                "total_connections": pool_metrics.total_connections
            },
            "cache_stats": cache_stats
        }
    
    async def close(self):
        """Close optimizer and cleanup resources"""
        perf_logger.info("Closing preference query optimizer")
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        # Dispose database engine
        self.engine.dispose()
        
        # Clear cache
        self.clear_cache()
        
        perf_logger.info("Preference query optimizer closed")

# Global optimizer instance (will be initialized by the application)
_global_optimizer: Optional[PreferenceQueryOptimizer] = None

def get_preference_query_optimizer() -> Optional[PreferenceQueryOptimizer]:
    """Get global preference query optimizer instance"""
    return _global_optimizer

def initialize_preference_query_optimizer(
    connection_string: str,
    **kwargs
) -> PreferenceQueryOptimizer:
    """Initialize global preference query optimizer"""
    global _global_optimizer
    _global_optimizer = PreferenceQueryOptimizer(connection_string, **kwargs)
    return _global_optimizer

async def close_preference_query_optimizer():
    """Close global preference query optimizer"""
    global _global_optimizer
    if _global_optimizer:
        await _global_optimizer.close()
        _global_optimizer = None