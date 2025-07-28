"""
Memory Manager for intelligent context and pattern storage
Manages short-term and long-term memory with decay and relevance scoring
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
import redis
from redis.asyncio import Redis
import logging

from ...models.memory_store import MemoryEntry, MemoryType, MemoryStore
from ...utils.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class MemoryScore:
    """Represents a memory's relevance score with decay factors"""
    relevance: float = 1.0
    recency: float = 1.0
    frequency: float = 1.0
    importance: float = 1.0
    
    @property
    def composite_score(self) -> float:
        """Calculate composite score with weighted factors"""
        return (
            self.relevance * 0.4 +
            self.recency * 0.3 +
            self.frequency * 0.2 +
            self.importance * 0.1
        )


class MemoryManager:
    """
    Intelligent memory manager with pattern learning and decay
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        memory_store: Optional[MemoryStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.memory_store = memory_store or MemoryStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        # Memory configuration
        self.short_term_ttl = 3600  # 1 hour
        self.medium_term_ttl = 86400  # 24 hours
        self.long_term_ttl = 2592000  # 30 days
        
        # Decay parameters
        self.recency_decay_rate = 0.1  # Decay rate per hour
        self.frequency_boost_factor = 0.1  # Boost per access
        
        # Memory pools
        self._short_term_pool: Dict[str, MemoryEntry] = {}
        self._pattern_cache: Dict[str, List[str]] = defaultdict(list)
        
    async def initialize(self):
        """Initialize Redis connection and memory store"""
        self.redis_client = await Redis.from_url(
            self.redis_url,
            decode_responses=True
        )
        await self.memory_store.initialize()
        logger.info("Memory Manager initialized")
        
    async def store_memory(
        self,
        key: str,
        content: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0
    ) -> str:
        """
        Store a memory with automatic classification and embedding
        
        Args:
            key: Memory key/identifier
            content: Memory content
            memory_type: Type of memory (short/long term)
            metadata: Additional metadata
            importance: Importance score (0-1)
            
        Returns:
            Memory ID
        """
        # Generate embedding for semantic search
        embedding = await self.embedding_generator.generate(str(content))
        
        # Create memory entry
        entry = MemoryEntry(
            key=key,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=1
        )
        
        # Store in appropriate location based on type
        if memory_type == MemoryType.SHORT_TERM:
            self._short_term_pool[key] = entry
            await self._store_redis_cache(key, entry, self.short_term_ttl)
        else:
            await self.memory_store.store(entry)
            await self._store_redis_cache(key, entry, self.long_term_ttl)
            
        # Update pattern cache
        await self._update_pattern_cache(key, content)
        
        logger.info(f"Stored memory: {key} (type: {memory_type.value})")
        return entry.id
        
    async def retrieve_memory(
        self,
        key: str,
        boost_access: bool = True
    ) -> Optional[MemoryEntry]:
        """
        Retrieve a memory by key with access tracking
        
        Args:
            key: Memory key
            boost_access: Whether to boost frequency score
            
        Returns:
            Memory entry if found
        """
        # Check short-term pool first
        if key in self._short_term_pool:
            entry = self._short_term_pool[key]
            if boost_access:
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
            return entry
            
        # Check Redis cache
        cached = await self._get_redis_cache(key)
        if cached:
            if boost_access:
                await self._boost_memory_access(key)
            return cached
            
        # Check persistent store
        entry = await self.memory_store.get(key)
        if entry and boost_access:
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            await self.memory_store.update(entry)
            
        return entry
        
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        min_score: float = 0.5
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        Search memories using semantic similarity and relevance scoring
        
        Args:
            query: Search query
            limit: Maximum results
            memory_types: Filter by memory types
            min_score: Minimum relevance score
            
        Returns:
            List of (memory, score) tuples
        """
        # Generate query embedding
        query_embedding = await self.embedding_generator.generate(query)
        
        # Search across all memory sources
        candidates = []
        
        # Search short-term pool
        for entry in self._short_term_pool.values():
            if memory_types and entry.memory_type not in memory_types:
                continue
            score = await self._calculate_relevance_score(entry, query_embedding)
            if score.composite_score >= min_score:
                candidates.append((entry, score.composite_score))
                
        # Search persistent store
        stored_memories = await self.memory_store.search_by_embedding(
            query_embedding,
            limit=limit * 2,  # Get more candidates for scoring
            memory_types=memory_types
        )
        
        for entry in stored_memories:
            score = await self._calculate_relevance_score(entry, query_embedding)
            if score.composite_score >= min_score:
                candidates.append((entry, score.composite_score))
                
        # Sort by score and return top results
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]
        
    async def detect_patterns(
        self,
        context: Dict[str, Any],
        min_support: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns in memory based on context
        
        Args:
            context: Current context
            min_support: Minimum pattern support threshold
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Analyze access patterns
        access_patterns = await self._analyze_access_patterns()
        for pattern in access_patterns:
            if pattern["support"] >= min_support:
                patterns.append({
                    "type": "access_pattern",
                    "pattern": pattern["pattern"],
                    "support": pattern["support"],
                    "confidence": pattern["confidence"]
                })
                
        # Analyze semantic patterns
        semantic_patterns = await self._analyze_semantic_patterns(context)
        patterns.extend(semantic_patterns)
        
        # Analyze temporal patterns
        temporal_patterns = await self._analyze_temporal_patterns()
        patterns.extend(temporal_patterns)
        
        return patterns
        
    async def consolidate_memories(
        self,
        time_window: timedelta = timedelta(hours=24)
    ) -> int:
        """
        Consolidate short-term memories into long-term based on patterns
        
        Args:
            time_window: Time window for consolidation
            
        Returns:
            Number of memories consolidated
        """
        cutoff_time = datetime.utcnow() - time_window
        consolidated_count = 0
        
        # Find memories to consolidate
        to_consolidate = []
        for key, entry in list(self._short_term_pool.items()):
            if entry.created_at <= cutoff_time:
                # Calculate importance for consolidation
                score = await self._calculate_consolidation_score(entry)
                if score >= 0.5:  # Consolidation threshold
                    to_consolidate.append(entry)
                    
        # Consolidate memories
        for entry in to_consolidate:
            # Convert to long-term memory
            entry.memory_type = MemoryType.LONG_TERM
            await self.memory_store.store(entry)
            
            # Remove from short-term pool
            del self._short_term_pool[entry.key]
            
            # Update cache
            await self._store_redis_cache(entry.key, entry, self.long_term_ttl)
            
            consolidated_count += 1
            
        logger.info(f"Consolidated {consolidated_count} memories")
        return consolidated_count
        
    async def apply_decay(self) -> int:
        """
        Apply decay to memories and clean up expired ones
        
        Returns:
            Number of memories removed
        """
        removed_count = 0
        current_time = datetime.utcnow()
        
        # Decay short-term memories
        for key in list(self._short_term_pool.keys()):
            entry = self._short_term_pool[key]
            age_hours = (current_time - entry.last_accessed).total_seconds() / 3600
            
            # Calculate decay factor
            decay_factor = np.exp(-self.recency_decay_rate * age_hours)
            
            # Remove if decayed below threshold
            if decay_factor < 0.1:  # 10% threshold
                del self._short_term_pool[key]
                removed_count += 1
                
        # Clean up Redis cache
        # This is handled by Redis TTL automatically
        
        logger.info(f"Applied decay, removed {removed_count} memories")
        return removed_count
        
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "short_term_count": len(self._short_term_pool),
            "long_term_count": await self.memory_store.count(),
            "pattern_cache_size": len(self._pattern_cache),
            "total_accesses": sum(
                entry.access_count for entry in self._short_term_pool.values()
            ),
            "avg_importance": np.mean([
                entry.importance for entry in self._short_term_pool.values()
            ]) if self._short_term_pool else 0
        }
        
    # Private helper methods
    
    async def _store_redis_cache(
        self,
        key: str,
        entry: MemoryEntry,
        ttl: int
    ):
        """Store memory in Redis cache"""
        if self.redis_client:
            cache_key = f"memory:{key}"
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(entry.to_dict())
            )
            
    async def _get_redis_cache(self, key: str) -> Optional[MemoryEntry]:
        """Get memory from Redis cache"""
        if self.redis_client:
            cache_key = f"memory:{key}"
            data = await self.redis_client.get(cache_key)
            if data:
                return MemoryEntry.from_dict(json.loads(data))
        return None
        
    async def _boost_memory_access(self, key: str):
        """Boost memory access count in cache"""
        if self.redis_client:
            cache_key = f"memory:access:{key}"
            await self.redis_client.incr(cache_key)
            await self.redis_client.expire(cache_key, self.medium_term_ttl)
            
    async def _calculate_relevance_score(
        self,
        entry: MemoryEntry,
        query_embedding: np.ndarray
    ) -> MemoryScore:
        """Calculate comprehensive relevance score"""
        # Semantic relevance
        relevance = float(np.dot(entry.embedding, query_embedding))
        
        # Recency score
        age_hours = (datetime.utcnow() - entry.last_accessed).total_seconds() / 3600
        recency = float(np.exp(-self.recency_decay_rate * age_hours))
        
        # Frequency score
        frequency = min(1.0, entry.access_count * self.frequency_boost_factor)
        
        return MemoryScore(
            relevance=relevance,
            recency=recency,
            frequency=frequency,
            importance=entry.importance
        )
        
    async def _calculate_consolidation_score(self, entry: MemoryEntry) -> float:
        """Calculate score for memory consolidation"""
        # Factors: access frequency, importance, recency
        frequency_score = min(1.0, entry.access_count / 10)  # Normalize to 10 accesses
        age_days = (datetime.utcnow() - entry.created_at).days
        age_score = 1.0 if age_days < 1 else 0.5
        
        return (
            frequency_score * 0.4 +
            entry.importance * 0.4 +
            age_score * 0.2
        )
        
    async def _update_pattern_cache(self, key: str, content: Any):
        """Update pattern cache for fast pattern detection"""
        # Extract patterns from content
        if isinstance(content, dict):
            for field, value in content.items():
                pattern_key = f"field:{field}"
                self._pattern_cache[pattern_key].append(key)
                
    async def _analyze_access_patterns(self) -> List[Dict[str, Any]]:
        """Analyze memory access patterns"""
        patterns = []
        
        # Analyze co-access patterns
        access_sequences = defaultdict(int)
        
        # This would be populated by tracking actual access sequences
        # For now, return empty list
        return patterns
        
    async def _analyze_semantic_patterns(
        self,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze semantic patterns in memories"""
        patterns = []
        
        # Group memories by semantic similarity
        # This would use clustering algorithms on embeddings
        # For now, return empty list
        return patterns
        
    async def _analyze_temporal_patterns(self) -> List[Dict[str, Any]]:
        """Analyze temporal patterns in memory access"""
        patterns = []
        
        # Analyze time-based access patterns
        # This would look for periodic access, bursts, etc.
        # For now, return empty list
        return patterns
        
    async def close(self):
        """Close connections and cleanup"""
        if self.redis_client:
            await self.redis_client.close()
        await self.memory_store.close()
        logger.info("Memory Manager closed")