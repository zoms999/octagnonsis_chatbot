"""
Vector search functionality using pgvector for semantic similarity search
Implements similarity search queries, result ranking, filtering, and performance monitoring
"""

import logging
import time
from datetime import datetime
import asyncio
import random
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from pgvector.sqlalchemy import Vector

from database.models import ChatDocument, ChatUser, DocumentType
from database.connection import get_async_session
from database.cache import LRUCache
from monitoring.metrics import observe as metrics_observe, inc as metrics_inc

logger = logging.getLogger(__name__)

class SimilarityMetric(str, Enum):
    """Supported similarity metrics for vector search"""
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "inner_product"

class SearchResultRanking(str, Enum):
    """Search result ranking strategies"""
    SIMILARITY_ONLY = "similarity_only"
    RECENCY_WEIGHTED = "recency_weighted"
    TYPE_PRIORITIZED = "type_prioritized"
    HYBRID = "hybrid"

@dataclass
class SearchResult:
    """Individual search result with metadata"""
    document: ChatDocument
    similarity_score: float
    rank: int
    search_metadata: Dict[str, Any]

@dataclass
class SearchQuery:
    """Search query configuration"""
    user_id: UUID
    query_vector: List[float]
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    limit: int = 5
    similarity_threshold: float = 0.7
    doc_type_filter: Optional[List[str]] = None
    ranking_strategy: SearchResultRanking = SearchResultRanking.SIMILARITY_ONLY
    include_metadata: bool = True

@dataclass
class SearchPerformanceMetrics:
    """Performance metrics for search operations"""
    query_time_ms: float
    total_documents_searched: int
    results_returned: int
    similarity_threshold: float
    search_timestamp: datetime
    user_id: UUID

class VectorSearchError(Exception):
    """Custom exception for vector search operations"""
    pass

class VectorSearchService:
    """Service for performing vector similarity searches with pgvector"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._performance_metrics: List[SearchPerformanceMetrics] = []
        # Cache for common queries per user (keyed by user + vector hash + filters)
        self._result_cache = LRUCache(capacity=1000, ttl_seconds=300)
    
    async def similarity_search(self, search_query: SearchQuery) -> List[SearchResult]:
        """
        Perform similarity search using pgvector
        
        Args:
            search_query: Search configuration and parameters
            
        Returns:
            List of SearchResult objects ranked by similarity
            
        Raises:
            VectorSearchError: If search operation fails
        """
        start_time = time.time()
        
        try:
            # Validate query vector - handle both List[float] and EmbeddingResult
            query_vector = search_query.query_vector
            if hasattr(query_vector, 'embedding'):
                # Handle EmbeddingResult object
                query_vector = query_vector.embedding
                search_query.query_vector = query_vector  # Update for consistency
            
            if not query_vector or len(query_vector) != 768:
                raise VectorSearchError("Query vector must be 768-dimensional")
            
            # Build base query
            stmt = self._build_similarity_query(search_query)
            
            # Cache key (rounded vector for stability)
            vec = tuple(round(v, 3) for v in search_query.query_vector[:16])  # prefix for key size
            cache_key = f"u:{search_query.user_id}|m:{search_query.similarity_metric}|t:{search_query.similarity_threshold}|l:{search_query.limit}|f:{','.join(search_query.doc_type_filter or [])}|v:{vec}"
            cached = await self._result_cache.get(cache_key)
            if cached is not None:
                logger.debug("Vector search cache hit")
                return cached

            # Execute search with retry and exponential backoff
            rows = None
            max_attempts = 3
            base_delay = 0.3
            for attempt in range(max_attempts):
                try:
                    result = await self.session.execute(stmt)
                    rows = result.fetchall()
                    break
                except SQLAlchemyError as e:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                        logger.warning(
                            f"Vector search DB error (attempt {attempt+1}/{max_attempts}): {e}. Retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(f"Database error in similarity search after retries: {e}")
                    raise
            
            # Process results
            search_results = await self._process_search_results(
                rows, search_query.ranking_strategy, search_query.include_metadata
            )

            # Store in cache
            await self._result_cache.set(cache_key, search_results)
            
            # Record performance metrics
            query_time_ms = (time.time() - start_time) * 1000
            await metrics_observe("vector_search_query_ms", query_time_ms)
            await self._record_performance_metrics(
                query_time_ms, len(rows), len(search_results), 
                search_query.similarity_threshold, search_query.user_id
            )
            
            logger.info(f"Vector search completed: {len(search_results)} results in {query_time_ms:.2f}ms")
            return search_results
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in similarity search: {e}")
            await metrics_inc("vector_search_errors_total")
            raise VectorSearchError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in similarity search: {e}")
            await metrics_inc("vector_search_errors_total")
            raise VectorSearchError(f"Search error: {str(e)}")
    
    async def search_by_document_type(
        self, 
        user_id: UUID, 
        query_vector: List[float], 
        doc_type: str,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for documents of a specific type
        
        Args:
            user_id: User UUID
            query_vector: 768-dimensional query vector
            doc_type: Document type to search
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of SearchResult objects
        """
        search_query = SearchQuery(
            user_id=user_id,
            query_vector=query_vector,
            doc_type_filter=[doc_type],
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return await self.similarity_search(search_query)
    
    async def multi_type_search(
        self, 
        user_id: UUID, 
        query_vector: List[float],
        doc_types: List[str],
        limit_per_type: int = 3
    ) -> Dict[str, List[SearchResult]]:
        """
        Search across multiple document types with separate limits
        
        Args:
            user_id: User UUID
            query_vector: 768-dimensional query vector
            doc_types: List of document types to search
            limit_per_type: Maximum results per document type
            
        Returns:
            Dictionary mapping document types to search results
        """
        results = {}
        
        for doc_type in doc_types:
            try:
                type_results = await self.search_by_document_type(
                    user_id, query_vector, doc_type, limit_per_type
                )
                results[doc_type] = type_results
            except VectorSearchError as e:
                logger.warning(f"Search failed for document type {doc_type}: {e}")
                results[doc_type] = []
        
        return results
    
    async def hybrid_search(
        self, 
        user_id: UUID, 
        query_vector: List[float],
        text_query: Optional[str] = None,
        limit: int = 5,
        vector_weight: float = 0.7,
        text_weight: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector similarity and text search
        
        Args:
            user_id: User UUID
            query_vector: 768-dimensional query vector
            text_query: Optional text query for full-text search
            limit: Maximum results to return
            vector_weight: Weight for vector similarity score
            text_weight: Weight for text search score
            
        Returns:
            List of SearchResult objects with hybrid scores
        """
        try:
            if text_query:
                # For now, use vector-only search with text query as metadata
                # TODO: Implement proper full-text search integration
                search_query = SearchQuery(
                    user_id=user_id,
                    query_vector=query_vector,
                    limit=limit,
                    ranking_strategy=SearchResultRanking.HYBRID
                )
                vector_results = await self.similarity_search(search_query)
                
                # Add text query information to metadata
                for result in vector_results:
                    result.search_metadata.update({
                        'text_query': text_query,
                        'search_type': 'hybrid_vector_only',
                        'note': 'Full-text search not implemented yet'
                    })
                
                return vector_results
            else:
                # Vector-only search
                search_query = SearchQuery(
                    user_id=user_id,
                    query_vector=query_vector,
                    limit=limit,
                    ranking_strategy=SearchResultRanking.HYBRID
                )
                return await self.similarity_search(search_query)
            
            result = await self.session.execute(stmt)
            rows = result.fetchall()
            
            # Process hybrid results
            search_results = []
            for i, (document, vector_sim, text_rank) in enumerate(rows):
                hybrid_score = vector_weight * vector_sim + text_weight * (text_rank or 0)
                
                search_results.append(SearchResult(
                    document=document,
                    similarity_score=hybrid_score,
                    rank=i + 1,
                    search_metadata={
                        'vector_similarity': vector_sim,
                        'text_rank': text_rank or 0,
                        'hybrid_score': hybrid_score,
                        'search_type': 'hybrid'
                    }
                ))
            
            return search_results
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in hybrid search: {e}")
            raise VectorSearchError(f"Hybrid search error: {str(e)}")
    
    async def get_similar_documents(
        self, 
        document_id: UUID, 
        limit: int = 5,
        exclude_same_type: bool = False
    ) -> List[SearchResult]:
        """
        Find documents similar to a given document
        
        Args:
            document_id: Source document UUID
            limit: Maximum results to return
            exclude_same_type: Whether to exclude documents of the same type
            
        Returns:
            List of similar documents
        """
        try:
            # Get source document
            source_doc = await self.session.get(ChatDocument, document_id)
            if not source_doc:
                raise VectorSearchError(f"Source document {document_id} not found")
            
            # Build similarity query
            stmt = select(
                ChatDocument,
                (1 - ChatDocument.embedding_vector.cosine_distance(source_doc.embedding_vector)).label('similarity')
            ).where(
                and_(
                    ChatDocument.user_id == source_doc.user_id,
                    ChatDocument.doc_id != document_id,
                    (1 - ChatDocument.embedding_vector.cosine_distance(source_doc.embedding_vector)) > 0.5
                )
            )
            
            if exclude_same_type:
                stmt = stmt.where(ChatDocument.doc_type != source_doc.doc_type)
            
            stmt = stmt.order_by(text('similarity DESC')).limit(limit)
            
            result = await self.session.execute(stmt)
            rows = result.fetchall()
            
            # Process results
            search_results = []
            for i, (document, similarity) in enumerate(rows):
                search_results.append(SearchResult(
                    document=document,
                    similarity_score=similarity,
                    rank=i + 1,
                    search_metadata={
                        'source_document_id': str(document_id),
                        'search_type': 'similar_documents'
                    }
                ))
            
            return search_results
            
        except SQLAlchemyError as e:
            logger.error(f"Error finding similar documents: {e}")
            raise VectorSearchError(f"Similar documents search error: {str(e)}")
    
    async def get_search_performance_metrics(
        self, 
        user_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[SearchPerformanceMetrics]:
        """
        Get recent search performance metrics
        
        Args:
            user_id: Optional user filter
            limit: Maximum metrics to return
            
        Returns:
            List of performance metrics
        """
        metrics = self._performance_metrics[-limit:]
        
        if user_id:
            metrics = [m for m in metrics if m.user_id == user_id]
        
        return sorted(metrics, key=lambda x: x.search_timestamp, reverse=True)

    async def benchmark_query(self, search_query: SearchQuery, runs: int = 5) -> Dict[str, Any]:
        """Benchmark a given search query across multiple runs."""
        timings = []
        for _ in range(max(1, runs)):
            start = time.time()
            try:
                await self.similarity_search(search_query)
            except Exception:
                pass
            timings.append((time.time() - start) * 1000)
        return {
            "runs": runs,
            "avg_ms": sum(timings) / len(timings),
            "min_ms": min(timings),
            "max_ms": max(timings)
        }
    
    async def optimize_search_performance(self) -> Dict[str, Any]:
        """
        Analyze and provide recommendations for search performance optimization
        
        Returns:
            Dictionary with performance analysis and recommendations
        """
        if not self._performance_metrics:
            return {"message": "No performance metrics available"}
        
        recent_metrics = self._performance_metrics[-100:]
        
        avg_query_time = sum(m.query_time_ms for m in recent_metrics) / len(recent_metrics)
        max_query_time = max(m.query_time_ms for m in recent_metrics)
        min_query_time = min(m.query_time_ms for m in recent_metrics)
        
        avg_results = sum(m.results_returned for m in recent_metrics) / len(recent_metrics)
        
        recommendations = []
        
        if avg_query_time > 500:  # 500ms threshold
            recommendations.append("Consider optimizing HNSW index parameters")
        
        if max_query_time > 2000:  # 2s threshold
            recommendations.append("Some queries are very slow - check for missing indexes")
        
        if avg_results < 2:
            recommendations.append("Low result counts - consider lowering similarity threshold")
        
        return {
            "performance_summary": {
                "average_query_time_ms": avg_query_time,
                "max_query_time_ms": max_query_time,
                "min_query_time_ms": min_query_time,
                "average_results_returned": avg_results,
                "total_queries_analyzed": len(recent_metrics)
            },
            "recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    # Private helper methods
    def _build_similarity_query(self, search_query: SearchQuery):
        """Build SQLAlchemy query for similarity search"""
        # Select documents with similarity scores
        if search_query.similarity_metric == SimilarityMetric.COSINE:
            similarity_expr = (1 - ChatDocument.embedding_vector.cosine_distance(search_query.query_vector))
            index_ops = 'vector_cosine_ops'
        elif search_query.similarity_metric == SimilarityMetric.L2:
            similarity_expr = (1 / (1 + ChatDocument.embedding_vector.l2_distance(search_query.query_vector)))
            index_ops = 'vector_l2_ops'
        else:  # INNER_PRODUCT
            similarity_expr = ChatDocument.embedding_vector.inner_product(search_query.query_vector)
            index_ops = 'vector_ip_ops'
        
        stmt = select(
            ChatDocument,
            similarity_expr.label('similarity')
        ).where(
            and_(
                ChatDocument.user_id == search_query.user_id,
                similarity_expr > search_query.similarity_threshold
            )
        )
        
        # Apply document type filter
        if search_query.doc_type_filter:
            stmt = stmt.where(ChatDocument.doc_type.in_(search_query.doc_type_filter))
        
        # Apply ordering and limit
        stmt = stmt.order_by(text('similarity DESC')).limit(search_query.limit)
        
        return stmt
    
    async def _process_search_results(
        self, 
        rows: List[Tuple], 
        ranking_strategy: SearchResultRanking,
        include_metadata: bool
    ) -> List[SearchResult]:
        """Process raw search results into SearchResult objects"""
        if not rows:
            return []
        
        search_results = []
        
        for i, (document, similarity) in enumerate(rows):
            metadata = {}
            
            if include_metadata:
                # Handle timezone-aware datetime comparison
                doc_created = document.created_at
                if doc_created.tzinfo is not None:
                    # Document has timezone info, make utcnow timezone-aware
                    from datetime import timezone
                    current_time = datetime.now(timezone.utc)
                else:
                    # Document is naive, use naive utcnow
                    current_time = datetime.utcnow()
                
                metadata.update({
                    'original_rank': i + 1,
                    'document_age_days': (current_time - doc_created).days,
                    'document_type': document.doc_type,
                    'content_length': len(document.summary_text)
                })
            
            # Apply ranking strategy adjustments
            adjusted_score = similarity
            
            if ranking_strategy == SearchResultRanking.RECENCY_WEIGHTED:
                # Boost recent documents
                doc_created = document.created_at
                if doc_created.tzinfo is not None:
                    from datetime import timezone
                    current_time = datetime.now(timezone.utc)
                else:
                    current_time = datetime.utcnow()
                age_days = (current_time - doc_created).days
                recency_boost = max(0, 1 - (age_days / 30))  # Boost decreases over 30 days
                adjusted_score = similarity * (1 + 0.1 * recency_boost)
                metadata['recency_boost'] = recency_boost
            
            elif ranking_strategy == SearchResultRanking.TYPE_PRIORITIZED:
                # Prioritize certain document types
                type_priorities = {
                    DocumentType.PERSONALITY_PROFILE: 1.2,
                    DocumentType.CAREER_RECOMMENDATIONS: 1.1,
                    DocumentType.THINKING_SKILLS: 1.0,
                    DocumentType.COMPETENCY_ANALYSIS: 0.9,
                    DocumentType.LEARNING_STYLE: 0.8,
                    DocumentType.PREFERENCE_ANALYSIS: 0.7
                }
                type_boost = type_priorities.get(document.doc_type, 1.0)
                adjusted_score = similarity * type_boost
                metadata['type_boost'] = type_boost
            
            elif ranking_strategy == SearchResultRanking.HYBRID:
                # Combine recency and type prioritization
                doc_created = document.created_at
                if doc_created.tzinfo is not None:
                    from datetime import timezone
                    current_time = datetime.now(timezone.utc)
                else:
                    current_time = datetime.utcnow()
                age_days = (current_time - doc_created).days
                recency_boost = max(0, 1 - (age_days / 30))
                
                type_priorities = {
                    DocumentType.PERSONALITY_PROFILE: 1.1,
                    DocumentType.CAREER_RECOMMENDATIONS: 1.05,
                    DocumentType.THINKING_SKILLS: 1.0,
                    DocumentType.COMPETENCY_ANALYSIS: 0.95,
                    DocumentType.LEARNING_STYLE: 0.9,
                    DocumentType.PREFERENCE_ANALYSIS: 0.85
                }
                type_boost = type_priorities.get(document.doc_type, 1.0)
                
                adjusted_score = similarity * type_boost * (1 + 0.05 * recency_boost)
                metadata.update({
                    'recency_boost': recency_boost,
                    'type_boost': type_boost
                })
            
            search_results.append(SearchResult(
                document=document,
                similarity_score=adjusted_score,
                rank=i + 1,  # Will be re-ranked if needed
                search_metadata=metadata
            ))
        
        # Re-rank if ranking strategy was applied
        if ranking_strategy != SearchResultRanking.SIMILARITY_ONLY:
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            for i, result in enumerate(search_results):
                result.rank = i + 1
        
        return search_results
    
    async def _record_performance_metrics(
        self, 
        query_time_ms: float, 
        total_searched: int, 
        results_returned: int,
        similarity_threshold: float, 
        user_id: UUID
    ):
        """Record performance metrics for monitoring"""
        metrics = SearchPerformanceMetrics(
            query_time_ms=query_time_ms,
            total_documents_searched=total_searched,
            results_returned=results_returned,
            similarity_threshold=similarity_threshold,
            search_timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        self._performance_metrics.append(metrics)
        
        # Keep only last 1000 metrics to prevent memory issues
        if len(self._performance_metrics) > 1000:
            self._performance_metrics = self._performance_metrics[-1000:]


# Factory function
async def get_vector_search_service(session: AsyncSession) -> VectorSearchService:
    """Factory function to create vector search service with session"""
    return VectorSearchService(session)