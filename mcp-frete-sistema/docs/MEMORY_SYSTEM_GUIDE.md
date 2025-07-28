# Intelligent Memory System Guide

## Overview

The MCP Freight System includes an intelligent memory system that provides pattern matching, semantic search, and continuous learning capabilities. This system enhances the MCP's ability to understand context, learn from interactions, and provide more relevant responses over time.

## Components

### 1. Memory Manager (`memory_manager.py`)

The core component that handles all memory operations with intelligent decay and consolidation.

**Features:**
- **Short-term memory**: Stores recent interactions (TTL: 1 hour)
- **Medium-term memory**: Stores session data (TTL: 24 hours)  
- **Long-term memory**: Stores learned patterns (TTL: 30 days)
- **Memory decay**: Automatic relevance scoring with time-based decay
- **Redis caching**: Fast access to frequently used memories
- **Semantic search**: Find memories by meaning, not just keywords

**Usage Example:**
```python
from src.services.memory import MemoryManager
from src.models.memory_store import MemoryType

# Initialize
memory_manager = MemoryManager(redis_url="redis://localhost:6379")
await memory_manager.initialize()

# Store a memory
await memory_manager.store_memory(
    key="freight_calculation_sp_rj",
    content={
        "route": "SP-RJ",
        "average_cost": 250.00,
        "average_days": 2
    },
    memory_type=MemoryType.LONG_TERM,
    metadata={"category": "freight_patterns"},
    importance=0.9
)

# Search memories semantically
results = await memory_manager.search_memories(
    query="São Paulo freight costs",
    limit=5,
    min_score=0.6
)

for memory, score in results:
    print(f"Found: {memory.key} (relevance: {score:.2f})")
```

### 2. Pattern Matcher (`pattern_matcher.py`)

Intelligent pattern recognition and learning from text data.

**Features:**
- **Multiple pattern types**: dates, numbers, entities, actions, structural
- **Pattern learning**: Automatically learns from repeated patterns
- **Entity extraction**: Extract freight-specific entities (products, clients, routes)
- **Pattern confidence**: Tracks pattern reliability
- **Domain-specific patterns**: Pre-configured for freight system

**Usage Example:**
```python
from src.services.memory import PatternMatcher

# Initialize
pattern_matcher = PatternMatcher()

# Learn from text
await pattern_matcher.learn_pattern(
    text="Calculate freight for order 12345 from SP to RJ, 150kg",
    pattern_type="entity",
    context={"domain": "freight"}
)

# Extract entities
entities = await pattern_matcher.extract_entities(
    text="Send 200kg to São Paulo by tomorrow"
)
# Result: {
#     "peso": ["200kg"],
#     "cidade": ["São Paulo"],
#     "data": ["tomorrow"]
# }

# Match patterns
matches = await pattern_matcher.match_patterns(
    text="What's the freight cost for 100kg?",
    pattern_types=["numeric", "action"]
)
```

### 3. Knowledge Base (`knowledge_base.py`)

Domain-specific knowledge management with continuous learning.

**Features:**
- **Structured knowledge**: Organized by categories and subcategories
- **Domain ontology**: Pre-configured freight system concepts
- **Confidence tracking**: Knowledge validation and scoring
- **Related knowledge**: Find connections between knowledge items
- **Import/Export**: YAML and JSON support

**Usage Example:**
```python
from src.services.memory import KnowledgeBase

# Initialize
knowledge_base = KnowledgeBase()
await knowledge_base.initialize()

# Add knowledge
await knowledge_base.add_knowledge(
    category="rules",
    subcategory="pricing",
    title="Weight-based freight calculation",
    content={
        "formula": "base_cost + (weight * rate_per_kg)",
        "base_cost_range": [20, 100],
        "rate_per_kg_range": [1.5, 5.0]
    },
    tags=["pricing", "calculation", "weight"],
    confidence=0.95
)

# Query knowledge
results = await knowledge_base.query_knowledge(
    query="freight pricing rules",
    categories=["rules"],
    min_confidence=0.7
)

# Learn from feedback
await knowledge_base.learn_from_interaction(
    query="How to calculate freight?",
    selected_result="rules:pricing:weight-based",
    feedback="Very helpful, exactly what I needed",
    success=True
)
```

### 4. Memory Store (`memory_store.py`)

Persistent storage layer with SQLite and embedding support.

**Features:**
- **Async SQLite**: Non-blocking database operations
- **Embedding storage**: Stores vector representations
- **Memory associations**: Track relationships between memories
- **Efficient indexing**: Fast retrieval by key, type, or similarity
- **Automatic cleanup**: Removes old, unused memories

### 5. Embedding Generator (`embeddings.py`)

Generates semantic embeddings for similarity search.

**Features:**
- **TF-IDF + LSA**: Lightweight alternative to transformers
- **Domain vocabulary**: Freight-specific term expansion
- **Embedding cache**: Reuses computed embeddings
- **Multiple metrics**: Cosine, Euclidean, Manhattan similarity
- **Cold start**: Works even without training data

## Integration Patterns

### 1. Query Enhancement

Enhance user queries with memory context:

```python
async def enhance_query(user_query: str):
    # Search for relevant memories
    memories = await memory_manager.search_memories(
        query=user_query,
        limit=3
    )
    
    # Extract patterns
    patterns = await pattern_matcher.match_patterns(
        text=user_query
    )
    
    # Find relevant knowledge
    knowledge = await knowledge_base.query_knowledge(
        query=user_query,
        min_confidence=0.7
    )
    
    # Combine into enhanced context
    context = {
        "original_query": user_query,
        "relevant_memories": [m.content for m, _ in memories],
        "detected_patterns": [p.pattern.pattern_value for p in patterns],
        "domain_knowledge": [k.content for k, _ in knowledge]
    }
    
    return context
```

### 2. Learning Pipeline

Continuous learning from interactions:

```python
async def learn_from_interaction(query, response, success, feedback=None):
    # Store interaction memory
    await memory_manager.store_memory(
        key=f"interaction:{datetime.utcnow().timestamp()}",
        content={
            "query": query,
            "response": response,
            "success": success,
            "feedback": feedback
        },
        memory_type=MemoryType.SHORT_TERM
    )
    
    # Learn patterns
    await pattern_matcher.learn_pattern(
        text=query,
        pattern_type="action"
    )
    
    # Update knowledge base
    if success and feedback:
        await knowledge_base.learn_from_interaction(
            query=query,
            selected_result=response.get("id"),
            feedback=feedback,
            success=success
        )
    
    # Consolidate if needed
    await memory_manager.consolidate_memories()
```

### 3. Context-Aware Responses

Use memory for contextual responses:

```python
async def generate_contextual_response(query):
    # Get user's recent interactions
    recent_memories = await memory_manager.search_memories(
        query=f"user:{user_id}",
        memory_types=[MemoryType.SHORT_TERM],
        limit=5
    )
    
    # Detect intent from patterns
    action_patterns = await pattern_matcher.match_patterns(
        text=query,
        pattern_types=["action"]
    )
    
    # Get domain knowledge
    relevant_knowledge = await knowledge_base.query_knowledge(
        query=query,
        categories=["rules", "processes"]
    )
    
    # Generate response with context
    response = await generate_response(
        query=query,
        context={
            "history": recent_memories,
            "intent": action_patterns,
            "knowledge": relevant_knowledge
        }
    )
    
    return response
```

## Configuration

### Redis Setup

```python
# Redis configuration for caching
REDIS_CONFIG = {
    "url": "redis://localhost:6379",
    "db": 0,
    "decode_responses": True,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "socket_keepalive": True,
    "socket_keepalive_options": {},
    "connection_pool_kwargs": {
        "max_connections": 50
    }
}
```

### Memory TTL Configuration

```python
# Memory time-to-live settings
MEMORY_TTL = {
    "short_term": 3600,      # 1 hour
    "medium_term": 86400,    # 24 hours
    "long_term": 2592000,    # 30 days
    "working": 1800,         # 30 minutes
    "episodic": 604800,      # 7 days
    "semantic": 7776000      # 90 days
}
```

### Pattern Learning Thresholds

```python
# Pattern learning configuration
PATTERN_CONFIG = {
    "min_support": 2,         # Minimum occurrences
    "confidence_threshold": 0.7,
    "confidence_boost": 0.05,  # Per successful use
    "confidence_decay": 0.1    # Per failed use
}
```

## Best Practices

### 1. Memory Key Naming

Use hierarchical keys for organization:
```
user:{user_id}:query:{timestamp}
pattern:{type}:{value}
knowledge:{category}:{subcategory}:{title}
session:{session_id}:context
```

### 2. Importance Scoring

Set importance based on:
- User actions (clicked = 0.9, viewed = 0.5)
- Data criticality (pricing = 0.9, info = 0.3)
- Frequency of access
- Business value

### 3. Memory Consolidation

Run consolidation:
- After each session
- Every hour for active systems
- When short-term memory exceeds threshold
- Before system shutdown

### 4. Pattern Validation

Validate patterns before learning:
- Check minimum support
- Verify against known good patterns
- Test pattern accuracy
- Monitor false positive rate

## Performance Optimization

### 1. Batch Operations

```python
# Batch memory operations
memories = [
    MemoryEntry(key=f"batch_{i}", content=data[i], ...)
    for i in range(len(data))
]

# Store all at once
await asyncio.gather(*[
    memory_manager.store_memory(m) for m in memories
])
```

### 2. Embedding Precomputation

```python
# Precompute embeddings for common queries
common_queries = ["freight cost", "delivery time", "track order"]
embeddings = await embedding_generator.generate_batch(common_queries)

# Cache for fast lookup
for query, embedding in zip(common_queries, embeddings):
    await cache.set(f"embedding:{query}", embedding)
```

### 3. Memory Pruning

```python
# Regular cleanup
async def prune_memories():
    # Remove old short-term memories
    removed = await memory_manager.apply_decay()
    
    # Clean up low-value memories
    cleaned = await memory_store.cleanup(
        max_age_days=30,
        min_importance=0.3,
        min_access_count=2
    )
    
    print(f"Pruned {removed + cleaned} memories")
```

## Monitoring

Track system health:

```python
async def get_memory_health():
    stats = {
        "memory": await memory_manager.get_memory_stats(),
        "patterns": await pattern_matcher.get_pattern_statistics(),
        "knowledge": await knowledge_base.get_statistics(),
        "store": await memory_store.get_statistics()
    }
    
    health = {
        "total_memories": stats["store"]["total_count"],
        "active_patterns": stats["patterns"]["total_patterns"],
        "knowledge_items": stats["knowledge"]["total_items"],
        "avg_importance": stats["memory"]["avg_importance"],
        "cache_hit_rate": calculate_cache_hit_rate()
    }
    
    return health
```

## Troubleshooting

### Common Issues

1. **High memory usage**: Increase decay rate or reduce TTL
2. **Slow searches**: Add more specific indices or reduce embedding dimensions
3. **Low pattern confidence**: Increase minimum support threshold
4. **Redis connection issues**: Check Redis server and network
5. **SQLite lock errors**: Use WAL mode or connection pooling

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("memory_manager").setLevel(logging.DEBUG)
logging.getLogger("pattern_matcher").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Transformer embeddings**: Integration with sentence-transformers
2. **Distributed memory**: Multi-node memory sharing
3. **Active learning**: Request user validation for uncertain patterns
4. **Memory visualization**: Graph-based memory exploration
5. **Export to vector databases**: Pinecone, Weaviate integration