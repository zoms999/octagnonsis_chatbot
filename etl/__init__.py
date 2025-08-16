"""
ETL Pipeline for Aptitude Chatbot RAG System
Provides data extraction, transformation, and loading capabilities
"""

from .legacy_query_executor import (
    LegacyQueryExecutor,
    QueryResult,
    QueryExecutionError,
    QueryValidationError
)

from .document_transformer import (
    DocumentTransformer,
    DocumentTransformationError
)

from .vector_embedder import (
    VectorEmbedder,
    EmbeddingError,
    EmbeddingCache
)

__all__ = [
    # Legacy query integration
    'LegacyQueryExecutor',
    'QueryResult',
    'QueryExecutionError',
    'QueryValidationError',
    
    # Document transformation
    'DocumentTransformer',
    'DocumentTransformationError',
    
    # Vector embedding
    'VectorEmbedder',
    'EmbeddingError',
    'EmbeddingCache'
]