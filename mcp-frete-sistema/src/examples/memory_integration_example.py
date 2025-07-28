"""
Example of how to integrate and use the intelligent memory system
Shows usage of MemoryManager, PatternMatcher, and KnowledgeBase
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from ..services.memory import MemoryManager, PatternMatcher, KnowledgeBase
from ..models.memory_store import MemoryType


async def demonstrate_memory_system():
    """Demonstrate the intelligent memory system capabilities"""
    
    # Initialize components
    memory_manager = MemoryManager(redis_url="redis://localhost:6379")
    pattern_matcher = PatternMatcher()
    knowledge_base = KnowledgeBase()
    
    # Initialize connections
    await memory_manager.initialize()
    await knowledge_base.initialize()
    
    print("=== Intelligent Memory System Demo ===\n")
    
    # 1. Store different types of memories
    print("1. Storing memories...")
    
    # Short-term memory: Recent query
    await memory_manager.store_memory(
        key="query:calculate_freight",
        content={
            "query": "Calcular frete para São Paulo",
            "parameters": {
                "origem": "Rio de Janeiro",
                "destino": "São Paulo",
                "peso": 150,
                "modalidade": "rodoviário"
            },
            "timestamp": datetime.utcnow().isoformat()
        },
        memory_type=MemoryType.SHORT_TERM,
        metadata={"user": "cliente_123", "session": "abc-123"},
        importance=0.8
    )
    
    # Long-term memory: Learned pattern
    await memory_manager.store_memory(
        key="pattern:freight_calculation",
        content={
            "pattern": "Freight calculations for SP-RJ route",
            "average_cost_per_kg": 2.5,
            "average_delivery_days": 2,
            "success_rate": 0.95
        },
        memory_type=MemoryType.LONG_TERM,
        importance=0.9
    )
    
    print("✓ Memories stored successfully\n")
    
    # 2. Pattern matching and learning
    print("2. Pattern matching and learning...")
    
    # Learn patterns from queries
    query_texts = [
        "Calcular frete para pedido 12345 de São Paulo para Rio de Janeiro",
        "Quanto custa enviar 200kg para SP saindo do RJ?",
        "Prazo de entrega RJ-SP para carga de 150 quilos",
        "Frete urgente Rio-São Paulo 100kg"
    ]
    
    for query in query_texts:
        # Learn patterns
        await pattern_matcher.learn_pattern(
            text=query,
            pattern_type="entity",
            context={"domain": "freight_calculation"}
        )
        
        # Match patterns
        matches = await pattern_matcher.match_patterns(
            text=query,
            pattern_types=["entity", "numeric", "action"]
        )
        
        print(f"Query: {query[:50]}...")
        print(f"Found {len(matches)} patterns")
        
        # Extract entities
        entities = await pattern_matcher.extract_entities(query)
        if entities:
            print(f"Entities: {entities}")
        print()
        
    # 3. Knowledge base operations
    print("3. Knowledge base learning...")
    
    # Add domain knowledge
    await knowledge_base.add_knowledge(
        category="rules",
        subcategory="freight_calculation",
        title="Weight-based pricing",
        content={
            "description": "Freight cost calculation based on weight",
            "formula": "base_cost + (weight * cost_per_kg)",
            "parameters": {
                "base_cost": {"min": 10, "max": 50},
                "cost_per_kg": {"min": 1.5, "max": 5.0}
            }
        },
        tags=["pricing", "calculation", "weight"],
        confidence=0.95
    )
    
    await knowledge_base.add_knowledge(
        category="entities",
        subcategory="routes",
        title="Popular freight routes",
        content={
            "routes": [
                {"origin": "Rio de Janeiro", "destination": "São Paulo", "distance": 430},
                {"origin": "São Paulo", "destination": "Belo Horizonte", "distance": 586},
                {"origin": "Rio de Janeiro", "destination": "Belo Horizonte", "distance": 434}
            ]
        },
        tags=["routes", "distances", "cities"],
        confidence=1.0
    )
    
    print("✓ Knowledge added to base\n")
    
    # 4. Semantic search
    print("4. Semantic memory search...")
    
    search_queries = [
        "frete São Paulo",
        "cálculo de peso",
        "prazo de entrega"
    ]
    
    for query in search_queries:
        results = await memory_manager.search_memories(
            query=query,
            limit=3,
            min_score=0.3
        )
        
        print(f"Search: '{query}'")
        print(f"Found {len(results)} relevant memories")
        for memory, score in results:
            print(f"  - {memory.key} (score: {score:.2f})")
        print()
        
    # 5. Knowledge querying
    print("5. Knowledge base queries...")
    
    knowledge_results = await knowledge_base.query_knowledge(
        query="freight calculation rules",
        categories=["rules"],
        min_confidence=0.7
    )
    
    print(f"Found {len(knowledge_results)} knowledge items")
    for item, relevance in knowledge_results[:3]:
        print(f"  - {item.title} (relevance: {relevance:.2f})")
        print(f"    Category: {item.category}/{item.subcategory}")
        print(f"    Tags: {', '.join(item.tags)}")
        print()
        
    # 6. Pattern detection
    print("6. Pattern detection...")
    
    context = {
        "recent_queries": query_texts,
        "domain": "freight_system"
    }
    
    detected_patterns = await memory_manager.detect_patterns(
        context=context,
        min_support=0.3
    )
    
    print(f"Detected {len(detected_patterns)} patterns")
    for pattern in detected_patterns:
        print(f"  - Type: {pattern['type']}")
        print(f"    Support: {pattern.get('support', 0):.2f}")
        print(f"    Confidence: {pattern.get('confidence', 0):.2f}")
        print()
        
    # 7. Memory consolidation
    print("7. Memory consolidation...")
    
    consolidated = await memory_manager.consolidate_memories()
    print(f"Consolidated {consolidated} memories from short-term to long-term\n")
    
    # 8. Statistics
    print("8. System statistics...")
    
    memory_stats = await memory_manager.get_memory_stats()
    pattern_stats = await pattern_matcher.get_pattern_statistics()
    knowledge_stats = await knowledge_base.get_statistics()
    
    print("Memory Manager:")
    print(f"  - Short-term memories: {memory_stats['short_term_count']}")
    print(f"  - Long-term memories: {memory_stats['long_term_count']}")
    print(f"  - Average importance: {memory_stats['avg_importance']:.2f}")
    
    print("\nPattern Matcher:")
    print(f"  - Total patterns: {pattern_stats['total_patterns']}")
    print(f"  - Average confidence: {pattern_stats['avg_confidence']:.2f}")
    
    print("\nKnowledge Base:")
    print(f"  - Total items: {knowledge_stats['total_items']}")
    print(f"  - Categories: {list(knowledge_stats['categories'].keys())}")
    
    # Cleanup
    await memory_manager.close()
    await knowledge_base.close()
    
    print("\n=== Demo completed successfully ===")


async def demonstrate_auto_learning():
    """Demonstrate auto-learning capabilities"""
    
    memory_manager = MemoryManager()
    pattern_matcher = PatternMatcher()
    knowledge_base = KnowledgeBase()
    
    await memory_manager.initialize()
    await knowledge_base.initialize()
    
    print("\n=== Auto-Learning Demo ===\n")
    
    # Simulate user interactions
    interactions = [
        {
            "query": "Calcular frete de 100kg de RJ para SP",
            "selected_result": "freight_calc_rj_sp",
            "success": True,
            "feedback": "Cálculo correto, prazo de 2 dias úteis"
        },
        {
            "query": "Qual o prazo de entrega para BH?",
            "selected_result": "delivery_time_bh",
            "success": True,
            "feedback": "3-4 dias úteis partindo de SP"
        },
        {
            "query": "Frete expresso disponível?",
            "selected_result": None,
            "success": False,
            "feedback": "Não encontrou opções de frete expresso"
        }
    ]
    
    for interaction in interactions:
        print(f"Query: {interaction['query']}")
        
        # Store the query
        await memory_manager.store_memory(
            key=f"interaction:{datetime.utcnow().timestamp()}",
            content=interaction,
            memory_type=MemoryType.SHORT_TERM
        )
        
        # Learn from interaction
        await knowledge_base.learn_from_interaction(
            query=interaction["query"],
            selected_result=interaction.get("selected_result"),
            feedback=interaction.get("feedback"),
            success=interaction["success"]
        )
        
        # Extract and learn patterns
        patterns = await pattern_matcher.learn_pattern(
            text=interaction["query"],
            pattern_type="action"
        )
        
        print(f"  Success: {interaction['success']}")
        print(f"  Learned {len(patterns)} patterns")
        print()
        
    # Show what was learned
    print("System learned:")
    
    # Recent patterns
    pattern_stats = await pattern_matcher.get_pattern_statistics()
    print(f"- {pattern_stats['total_patterns']} patterns identified")
    
    # Knowledge items
    knowledge_stats = await knowledge_base.get_statistics()
    print(f"- {knowledge_stats['total_items']} knowledge items stored")
    
    # Memory insights
    memory_stats = await memory_manager.get_memory_stats()
    print(f"- {memory_stats['short_term_count']} recent interactions tracked")
    
    await memory_manager.close()
    await knowledge_base.close()
    
    print("\n=== Auto-learning demo completed ===")


if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demonstrate_memory_system())
    asyncio.run(demonstrate_auto_learning())