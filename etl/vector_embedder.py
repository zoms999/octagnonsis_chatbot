"""
Vector Embedding Service
Integrates with Google Gemini API for text embedding generation
"""

import asyncio
import logging
import hashlib
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EmbeddingError(Exception):
    """Raised when embedding generation fails"""
    def __init__(self, text: str, error_message: str):
        self.text = text
        self.error_message = error_message
        super().__init__(f"Embedding generation failed for text: {error_message}")

@dataclass
class EmbeddingResult:
    """Result container for embedding generation"""
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    processing_time: float
    cached: bool = False

class EmbeddingCache:
    """
    In-memory cache for embeddings with TTL support
    In production, this should be replaced with Redis or similar
    """
    
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        self.cache: Dict[str, Tuple[List[float], datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.access_times: Dict[str, datetime] = {}
    
    def _generate_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model"""
        content = f"{text}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache if available and not expired"""
        key = self._generate_key(text, model)
        
        if key in self.cache:
            embedding, timestamp = self.cache[key]
            
            # Check if expired
            if datetime.now() - timestamp > self.ttl:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return None
            
            # Update access time
            self.access_times[key] = datetime.now()
            return embedding
        
        return None
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache"""
        key = self._generate_key(text, model)
        
        # If cache is full, remove oldest accessed item
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = (embedding, datetime.now())
        self.access_times[key] = datetime.now()
    
    def clear(self) -> None:
        """Clear all cached embeddings"""
        self.cache.clear()
        self.access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items"""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
        
        return len(expired_keys)

class VectorEmbedder:
    """
    Google Gemini embedding service with caching and error recovery
    """
    
    _singleton_instance = None

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "models/embedding-001",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        batch_size: int = 10,
        rate_limit_per_minute: int = 60,
        enable_cache: bool = True,
        cache_ttl_hours: int = 24
    ):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size
        self.rate_limit_per_minute = rate_limit_per_minute
        self.enable_cache = enable_cache
        
        # Initialize cache
        self.cache = EmbeddingCache(ttl_hours=cache_ttl_hours) if enable_cache else None
        
        # Rate limiting
        self.request_times: List[float] = []
        self.rate_limit_lock = asyncio.Lock()
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # API endpoint
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    @classmethod
    def instance(cls):
        """Return a process-wide singleton instance to maximize cache reuse."""
        if cls._singleton_instance is None:
            cls._singleton_instance = cls()
        return cls._singleton_instance
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': self.api_key
                }
            )
    
    async def _wait_for_rate_limit(self):
        """Implement rate limiting"""
        async with self.rate_limit_lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # If we're at the rate limit, wait
            if len(self.request_times) >= self.rate_limit_per_minute:
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, waiting {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    # Remove the oldest request after waiting
                    self.request_times.pop(0)
            
            # Record this request
            self.request_times.append(now)
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding generation"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (Gemini has token limits)
        max_chars = 30000  # Conservative limit
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.warning(f"Text truncated to {max_chars} characters for embedding")
        
        return text
    
    async def _generate_single_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text"""
        start_time = time.time()
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        if not processed_text:
            raise EmbeddingError(text, "Empty or invalid text after preprocessing")
        
        # Check cache first
        if self.cache:
            cached_embedding = self.cache.get(processed_text, self.model)
            if cached_embedding is not None:
                processing_time = time.time() - start_time
                logger.debug(f"Retrieved embedding from cache for text length {len(processed_text)}")
                return EmbeddingResult(
                    text=processed_text,
                    embedding=cached_embedding,
                    model=self.model,
                    dimensions=len(cached_embedding),
                    processing_time=processing_time,
                    cached=True
                )
        
        # Generate embedding via API
        for attempt in range(self.max_retries + 1):
            try:
                await self._ensure_session()
                await self._wait_for_rate_limit()
                
                # Prepare request
                url = f"{self.base_url}/{self.model}:embedContent"
                payload = {
                    "content": {
                        "parts": [{"text": processed_text}]
                    }
                }
                
                # Make API request
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract embedding
                        if 'embedding' in data and 'values' in data['embedding']:
                            embedding = data['embedding']['values']
                            
                            # Validate embedding
                            if not isinstance(embedding, list) or len(embedding) == 0:
                                raise EmbeddingError(text, "Invalid embedding format received")
                            
                            # Cache the result
                            if self.cache:
                                self.cache.set(processed_text, self.model, embedding)
                            
                            processing_time = time.time() - start_time
                            logger.debug(f"Generated embedding for text length {len(processed_text)} in {processing_time:.2f}s")
                            
                            return EmbeddingResult(
                                text=processed_text,
                                embedding=embedding,
                                model=self.model,
                                dimensions=len(embedding),
                                processing_time=processing_time,
                                cached=False
                            )
                        else:
                            raise EmbeddingError(text, "No embedding data in API response")
                    
                    elif response.status == 429:  # Rate limit
                        if attempt < self.max_retries:
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise EmbeddingError(text, "Rate limit exceeded after all retries")
                    
                    elif response.status == 400:  # Bad request
                        error_data = await response.json()
                        error_msg = error_data.get('error', {}).get('message', 'Bad request')
                        raise EmbeddingError(text, f"API error: {error_msg}")
                    
                    else:
                        if attempt < self.max_retries:
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(f"API error {response.status}, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            raise EmbeddingError(text, f"API error {response.status}: {error_text}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Network error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise EmbeddingError(text, f"Network error after all retries: {e}")
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Unexpected error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise EmbeddingError(text, f"Unexpected error after all retries: {e}")
        
        # This should never be reached
        raise EmbeddingError(text, "Failed to generate embedding after all attempts")
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            EmbeddingResult object
        """
        return await self._generate_single_embedding(text)
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of EmbeddingResult objects
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts in batches of {self.batch_size}")
        
        results = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_start_time = time.time()
            
            logger.debug(f"Processing batch {i//self.batch_size + 1}/{(len(texts) + self.batch_size - 1)//self.batch_size}")
            
            # Generate embeddings concurrently within batch
            tasks = [self._generate_single_embedding(text) for text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to generate embedding for text {i+j}: {result}")
                    # Create a dummy result for failed embeddings
                    results.append(EmbeddingResult(
                        text=batch[j],
                        embedding=[0.0] * 768,  # Default dimension
                        model=self.model,
                        dimensions=768,
                        processing_time=0.0,
                        cached=False
                    ))
                else:
                    results.append(result)
            
            batch_time = time.time() - batch_start_time
            logger.debug(f"Batch completed in {batch_time:.2f}s")
            
            # Small delay between batches to be respectful to the API
            if i + self.batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        successful_count = sum(1 for r in results if len(r.embedding) > 1)  # Not dummy embedding
        cached_count = sum(1 for r in results if r.cached)
        
        logger.info(
            f"Embedding generation completed: {successful_count}/{len(texts)} successful, "
            f"{cached_count} from cache"
        )
        
        return results
    
    async def generate_document_embeddings(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of documents
        
        Args:
            documents: List of document dictionaries with 'summary_text' field
            
        Returns:
            List of documents with added 'embedding_vector' field
        """
        if not documents:
            return []
        
        # Extract texts to embed (prioritize text_to_embed over summary_text)
        texts_to_embed = []
        for doc in documents:
            # ▼▼▼ [핵심 수정] text_to_embed 키를 우선적으로 사용 ▼▼▼
            text_to_embed = doc.get('text_to_embed', doc.get('summary_text', ''))
            if not text_to_embed:
                logger.warning(f"Document missing text_to_embed and summary_text: {doc.get('doc_type', 'unknown')}")
                text_to_embed = str(doc.get('content', ''))[:500]  # Fallback to content preview
            texts_to_embed.append(text_to_embed)
            # ▲▲▲ [핵심 수정 끝] ▲▲▲
        
        # Generate embeddings
        embedding_results = await self.generate_embeddings_batch(texts_to_embed)
        
        # Add embeddings to documents
        enhanced_documents = []
        for i, doc in enumerate(documents):
            enhanced_doc = doc.copy()
            enhanced_doc['embedding_vector'] = embedding_results[i].embedding
            enhanced_doc['embedding_metadata'] = {
                'model': embedding_results[i].model,
                'dimensions': embedding_results[i].dimensions,
                'processing_time': embedding_results[i].processing_time,
                'cached': embedding_results[i].cached,
                'generated_at': datetime.now().isoformat()
            }
            enhanced_documents.append(enhanced_doc)
        
        return enhanced_documents
    
    async def cleanup_cache(self) -> int:
        """Clean up expired cache entries"""
        if self.cache:
            return self.cache.cleanup_expired()
        return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {"cache_enabled": False}
        
        return {
            "cache_enabled": True,
            "cache_size": self.cache.size(),
            "max_size": self.cache.max_size,
            "ttl_hours": self.cache.ttl.total_seconds() / 3600
        }
    
    async def close(self):
        """Clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("VectorEmbedder resources cleaned up")

# Convenience function for simple embedding generation
async def generate_text_embedding(
    text: str, 
    api_key: Optional[str] = None,
    model: str = "models/embedding-001"
) -> List[float]:
    """
    Simple function to generate embedding for a single text
    
    Args:
        text: Text to generate embedding for
        api_key: Google API key (optional, will use environment variable)
        model: Embedding model to use
        
    Returns:
        List of float values representing the embedding
    """
    async with VectorEmbedder(api_key=api_key, model=model) as embedder:
        result = await embedder.generate_embedding(text)
        return result.embedding

# Convenience function for batch embedding generation
async def generate_text_embeddings_batch(
    texts: List[str],
    api_key: Optional[str] = None,
    model: str = "models/embedding-001",
    batch_size: int = 10
) -> List[List[float]]:
    """
    Simple function to generate embeddings for multiple texts
    
    Args:
        texts: List of texts to generate embeddings for
        api_key: Google API key (optional, will use environment variable)
        model: Embedding model to use
        batch_size: Number of texts to process in each batch
        
    Returns:
        List of embedding vectors
    """
    async with VectorEmbedder(api_key=api_key, model=model, batch_size=batch_size) as embedder:
        results = await embedder.generate_embeddings_batch(texts)
        return [result.embedding for result in results]