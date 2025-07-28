"""
Unit tests for memory management system
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import json
import pickle
from src.memory.memory_manager import (
    MemoryManager,
    MemoryStore,
    MemoryIndex,
    MemoryError,
    MemoryNotFoundError
)


class TestMemoryStore:
    """Test cases for memory store operations"""
    
    @pytest.fixture
    def memory_store(self, tmp_path):
        """Create memory store instance"""
        return MemoryStore(
            storage_path=str(tmp_path),
            max_size_mb=100,
            compression_enabled=True
        )
    
    @pytest.fixture
    def sample_memories(self):
        """Sample memory entries"""
        return [
            {
                "id": "mem-001",
                "key": "freight/calculation/sp-rj",
                "value": {
                    "origin": "São Paulo",
                    "destination": "Rio de Janeiro",
                    "distance": 430,
                    "base_rate": 150.00
                },
                "metadata": {
                    "created_at": "2024-01-15T10:00:00Z",
                    "ttl": 3600,
                    "tags": ["freight", "calculation", "route"]
                }
            },
            {
                "id": "mem-002", 
                "key": "user/preferences/user-123",
                "value": {
                    "default_service": "express",
                    "preferred_packaging": "standard",
                    "notification_method": "email"
                },
                "metadata": {
                    "created_at": "2024-01-15T09:00:00Z",
                    "ttl": 86400,
                    "tags": ["user", "preferences"]
                }
            }
        ]
    
    def test_store_memory_success(self, memory_store, sample_memories):
        """Test successful memory storage"""
        memory = sample_memories[0]
        
        result = memory_store.store(
            key=memory["key"],
            value=memory["value"],
            metadata=memory["metadata"]
        )
        
        assert result["success"] is True
        assert result["id"] is not None
        assert result["compressed"] == memory_store.compression_enabled
        
        # Verify stored data
        retrieved = memory_store.get(memory["key"])
        assert retrieved["value"] == memory["value"]
        assert retrieved["metadata"] == memory["metadata"]
    
    def test_store_memory_with_compression(self, memory_store):
        """Test memory storage with compression"""
        large_data = {
            "data": "x" * 10000,  # Large string
            "array": list(range(1000))
        }
        
        result = memory_store.store(
            key="large/data",
            value=large_data,
            compress=True
        )
        
        assert result["compressed"] is True
        assert result["size_bytes"] < len(str(large_data))  # Compressed size
        
        # Verify decompression works
        retrieved = memory_store.get("large/data")
        assert retrieved["value"] == large_data
    
    def test_store_memory_size_limit(self, memory_store):
        """Test memory size limit enforcement"""
        memory_store.max_size_mb = 0.001  # 1KB limit
        
        huge_data = {"data": "x" * 10000}
        
        with pytest.raises(MemoryError) as exc_info:
            memory_store.store("huge/data", huge_data)
        
        assert "exceeds size limit" in str(exc_info.value)
    
    def test_get_memory_not_found(self, memory_store):
        """Test getting non-existent memory"""
        with pytest.raises(MemoryNotFoundError):
            memory_store.get("non/existent/key")
    
    def test_get_memory_expired(self, memory_store, sample_memories):
        """Test getting expired memory"""
        memory = sample_memories[0]
        memory["metadata"]["ttl"] = 1  # 1 second TTL
        
        memory_store.store(
            key=memory["key"],
            value=memory["value"],
            metadata=memory["metadata"]
        )
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        with pytest.raises(MemoryNotFoundError) as exc_info:
            memory_store.get(memory["key"])
        
        assert "expired" in str(exc_info.value)
    
    def test_update_memory(self, memory_store, sample_memories):
        """Test memory update"""
        memory = sample_memories[0]
        
        # Store initial
        memory_store.store(
            key=memory["key"],
            value=memory["value"]
        )
        
        # Update
        new_value = memory["value"].copy()
        new_value["base_rate"] = 200.00
        
        result = memory_store.update(
            key=memory["key"],
            value=new_value
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        
        # Verify update
        retrieved = memory_store.get(memory["key"])
        assert retrieved["value"]["base_rate"] == 200.00
    
    def test_delete_memory(self, memory_store, sample_memories):
        """Test memory deletion"""
        memory = sample_memories[0]
        
        # Store
        memory_store.store(key=memory["key"], value=memory["value"])
        
        # Delete
        result = memory_store.delete(memory["key"])
        assert result["success"] is True
        
        # Verify deleted
        with pytest.raises(MemoryNotFoundError):
            memory_store.get(memory["key"])
    
    def test_list_memories(self, memory_store, sample_memories):
        """Test listing memories"""
        # Store multiple memories
        for memory in sample_memories:
            memory_store.store(
                key=memory["key"],
                value=memory["value"],
                metadata=memory["metadata"]
            )
        
        # List all
        all_memories = memory_store.list()
        assert len(all_memories) == len(sample_memories)
        
        # List with pattern
        freight_memories = memory_store.list(pattern="freight/*")
        assert len(freight_memories) == 1
        assert freight_memories[0]["key"].startswith("freight/")
    
    def test_clear_memories(self, memory_store, sample_memories):
        """Test clearing all memories"""
        # Store memories
        for memory in sample_memories:
            memory_store.store(key=memory["key"], value=memory["value"])
        
        # Clear all
        result = memory_store.clear()
        assert result["cleared"] == len(sample_memories)
        
        # Verify cleared
        assert len(memory_store.list()) == 0


class TestMemoryIndex:
    """Test cases for memory indexing and search"""
    
    @pytest.fixture
    def memory_index(self):
        """Create memory index instance"""
        return MemoryIndex(
            index_fields=["tags", "category", "user_id"],
            search_enabled=True
        )
    
    @pytest.fixture
    def indexed_memories(self):
        """Memories with indexable fields"""
        return [
            {
                "key": "freight/route/sp-rj",
                "value": {"distance": 430},
                "tags": ["freight", "route", "brazil"],
                "category": "routing",
                "user_id": None
            },
            {
                "key": "freight/route/sp-mg",
                "value": {"distance": 580},
                "tags": ["freight", "route", "brazil"],
                "category": "routing",
                "user_id": None
            },
            {
                "key": "user/prefs/123",
                "value": {"theme": "dark"},
                "tags": ["user", "preferences"],
                "category": "user_data",
                "user_id": "123"
            }
        ]
    
    def test_index_memory(self, memory_index, indexed_memories):
        """Test memory indexing"""
        for memory in indexed_memories:
            memory_index.index(
                key=memory["key"],
                fields={
                    "tags": memory["tags"],
                    "category": memory["category"],
                    "user_id": memory["user_id"]
                }
            )
        
        # Verify index size
        assert memory_index.size() == len(indexed_memories)
    
    def test_search_by_tag(self, memory_index, indexed_memories):
        """Test searching by tag"""
        # Index memories
        for memory in indexed_memories:
            memory_index.index(memory["key"], {
                "tags": memory["tags"],
                "category": memory["category"]
            })
        
        # Search by tag
        results = memory_index.search(field="tags", value="freight")
        assert len(results) == 2
        assert all("freight" in r["tags"] for r in results)
        
        # Search by multiple tags
        results = memory_index.search(field="tags", value=["freight", "route"])
        assert len(results) == 2
    
    def test_search_by_category(self, memory_index, indexed_memories):
        """Test searching by category"""
        for memory in indexed_memories:
            memory_index.index(memory["key"], {
                "category": memory["category"]
            })
        
        results = memory_index.search(field="category", value="routing")
        assert len(results) == 2
        
        results = memory_index.search(field="category", value="user_data")
        assert len(results) == 1
    
    def test_compound_search(self, memory_index, indexed_memories):
        """Test compound search with multiple criteria"""
        for memory in indexed_memories:
            memory_index.index(memory["key"], {
                "tags": memory["tags"],
                "category": memory["category"],
                "user_id": memory["user_id"]
            })
        
        # Search with multiple criteria
        results = memory_index.compound_search({
            "tags": "freight",
            "category": "routing"
        })
        
        assert len(results) == 2
        assert all(r["category"] == "routing" for r in results)
    
    def test_remove_from_index(self, memory_index, indexed_memories):
        """Test removing from index"""
        # Index all
        for memory in indexed_memories:
            memory_index.index(memory["key"], {"tags": memory["tags"]})
        
        # Remove one
        memory_index.remove(indexed_memories[0]["key"])
        
        # Verify removed
        results = memory_index.search(field="tags", value="freight")
        assert len(results) == 1
        assert results[0]["key"] != indexed_memories[0]["key"]
    
    def test_rebuild_index(self, memory_index, indexed_memories):
        """Test index rebuilding"""
        # Index memories
        for memory in indexed_memories:
            memory_index.index(memory["key"], {"tags": memory["tags"]})
        
        # Simulate corruption
        memory_index._corrupt_index()
        
        # Rebuild
        memory_index.rebuild(indexed_memories)
        
        # Verify rebuilt correctly
        results = memory_index.search(field="tags", value="freight")
        assert len(results) == 2


class TestMemoryManager:
    """Test cases for memory manager orchestration"""
    
    @pytest.fixture
    def memory_manager(self, tmp_path):
        """Create memory manager instance"""
        return MemoryManager(
            storage_path=str(tmp_path),
            cache_enabled=True,
            index_enabled=True
        )
    
    @pytest.fixture
    def complex_memory_data(self):
        """Complex memory data for testing"""
        return {
            "freight_calculations": [
                {
                    "route": "SP-RJ",
                    "distance": 430,
                    "rates": {"express": 200, "standard": 150}
                },
                {
                    "route": "SP-MG", 
                    "distance": 580,
                    "rates": {"express": 250, "standard": 180}
                }
            ],
            "user_sessions": {
                "user-123": {
                    "last_query": "freight SP to RJ",
                    "preferences": {"service": "express"}
                }
            }
        }
    
    def test_store_and_retrieve_complex(self, memory_manager, complex_memory_data):
        """Test storing and retrieving complex data"""
        # Store with namespace
        memory_manager.store(
            key="freight_data",
            value=complex_memory_data,
            namespace="calculations",
            tags=["freight", "rates", "routes"]
        )
        
        # Retrieve
        retrieved = memory_manager.get("freight_data", namespace="calculations")
        assert retrieved == complex_memory_data
    
    def test_namespace_isolation(self, memory_manager):
        """Test namespace isolation"""
        # Store same key in different namespaces
        memory_manager.store("config", {"version": 1}, namespace="app")
        memory_manager.store("config", {"version": 2}, namespace="user")
        
        # Retrieve from different namespaces
        app_config = memory_manager.get("config", namespace="app")
        user_config = memory_manager.get("config", namespace="user")
        
        assert app_config["version"] == 1
        assert user_config["version"] == 2
    
    def test_search_across_namespaces(self, memory_manager):
        """Test searching across namespaces"""
        # Store in multiple namespaces
        memory_manager.store(
            "route1", {"from": "SP"}, 
            namespace="routes",
            tags=["freight", "route"]
        )
        memory_manager.store(
            "calc1", {"rate": 150},
            namespace="calculations", 
            tags=["freight", "pricing"]
        )
        
        # Search by tag across namespaces
        results = memory_manager.search(tags=["freight"])
        assert len(results) >= 2
        
        # Search in specific namespace
        results = memory_manager.search(tags=["freight"], namespace="routes")
        assert len(results) == 1
    
    def test_bulk_operations(self, memory_manager):
        """Test bulk memory operations"""
        bulk_data = [
            {"key": f"item-{i}", "value": {"data": i}, "tags": ["bulk"]}
            for i in range(10)
        ]
        
        # Bulk store
        results = memory_manager.bulk_store(bulk_data, namespace="bulk_test")
        assert all(r["success"] for r in results)
        
        # Bulk get
        keys = [f"item-{i}" for i in range(10)]
        values = memory_manager.bulk_get(keys, namespace="bulk_test")
        assert len(values) == 10
        
        # Bulk delete
        delete_results = memory_manager.bulk_delete(keys[:5], namespace="bulk_test")
        assert sum(1 for r in delete_results if r["success"]) == 5
    
    def test_memory_persistence(self, memory_manager):
        """Test memory persistence across instances"""
        # Store data
        memory_manager.store("persistent", {"value": 42}, namespace="test")
        
        # Create new instance with same storage path
        new_manager = MemoryManager(
            storage_path=memory_manager.storage_path,
            cache_enabled=False  # Disable cache to test persistence
        )
        
        # Should retrieve persisted data
        retrieved = new_manager.get("persistent", namespace="test")
        assert retrieved["value"] == 42
    
    def test_memory_expiration_cleanup(self, memory_manager):
        """Test automatic cleanup of expired memories"""
        # Store with short TTL
        memory_manager.store(
            "temp1", {"data": 1}, 
            ttl=1,  # 1 second
            namespace="temp"
        )
        memory_manager.store(
            "temp2", {"data": 2},
            ttl=3600,  # 1 hour
            namespace="temp"
        )
        
        # Wait for first to expire
        import time
        time.sleep(2)
        
        # Run cleanup
        cleaned = memory_manager.cleanup_expired()
        assert cleaned >= 1
        
        # Verify cleanup
        with pytest.raises(MemoryNotFoundError):
            memory_manager.get("temp1", namespace="temp")
        
        # Second should still exist
        assert memory_manager.get("temp2", namespace="temp")["data"] == 2
    
    def test_memory_statistics(self, memory_manager):
        """Test memory statistics and monitoring"""
        # Store various data
        for i in range(5):
            memory_manager.store(
                f"key-{i}", 
                {"data": "x" * 100},
                namespace="stats_test",
                tags=["test"]
            )
        
        # Get statistics
        stats = memory_manager.get_statistics()
        
        assert stats["total_memories"] >= 5
        assert stats["total_size_bytes"] > 0
        assert "stats_test" in stats["namespaces"]
        assert stats["namespaces"]["stats_test"]["count"] == 5
    
    def test_memory_backup_restore(self, memory_manager, tmp_path):
        """Test memory backup and restore"""
        # Store data
        memory_manager.store("backup_test", {"important": True})
        
        # Backup
        backup_path = tmp_path / "backup.json"
        memory_manager.backup(str(backup_path))
        assert backup_path.exists()
        
        # Clear all
        memory_manager.clear_all()
        
        # Restore
        memory_manager.restore(str(backup_path))
        
        # Verify restored
        restored = memory_manager.get("backup_test")
        assert restored["important"] is True
    
    @patch('src.memory.memory_manager.redis_client')
    def test_redis_cache_integration(self, mock_redis, memory_manager):
        """Test Redis cache integration"""
        memory_manager.cache_enabled = True
        
        # Store should cache in Redis
        memory_manager.store("cached_key", {"data": "value"})
        
        # Get should check Redis first
        mock_redis.get.return_value = json.dumps({"data": "cached_value"})
        result = memory_manager.get("cached_key")
        
        assert result["data"] == "cached_value"
        mock_redis.get.assert_called()
    
    def test_concurrent_access(self, memory_manager):
        """Test thread-safe concurrent access"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def concurrent_operation(i):
            try:
                # Store
                memory_manager.store(f"concurrent-{i}", {"value": i})
                # Get
                value = memory_manager.get(f"concurrent-{i}")
                results.put((i, value["value"]))
            except Exception as e:
                errors.put((i, e))
        
        # Run concurrent operations
        threads = []
        for i in range(20):
            t = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify results
        assert errors.empty(), "No errors in concurrent operations"
        assert results.qsize() == 20
        
        # Check all values are correct
        while not results.empty():
            i, value = results.get()
            assert value == i