"""
Memory Store models for persistence
Handles storage and retrieval of memory entries with embeddings
"""

import json
import sqlite3
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import numpy as np
import aiosqlite
import logging

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory storage"""
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


@dataclass
class MemoryEntry:
    """Represents a memory entry with metadata and embeddings"""
    key: str
    content: Any
    memory_type: MemoryType
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 1
    importance: float = 1.0
    id: str = field(default="", init=False)
    
    def __post_init__(self):
        """Generate ID after initialization"""
        if not self.id:
            timestamp = int(self.created_at.timestamp() * 1000)
            self.id = f"{self.memory_type.value}_{self.key}_{timestamp}"
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = {
            "id": self.id,
            "key": self.key,
            "content": self.content if isinstance(self.content, (dict, list, str, int, float, bool)) else str(self.content),
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "importance": self.importance
        }
        
        # Handle numpy array embedding
        if self.embedding is not None:
            data["embedding"] = self.embedding.tolist()
            
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary"""
        # Parse dates
        created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        last_accessed = datetime.fromisoformat(data.get("last_accessed", datetime.utcnow().isoformat()))
        
        # Parse memory type
        memory_type = MemoryType(data.get("memory_type", "short_term"))
        
        # Parse embedding
        embedding = None
        if "embedding" in data and data["embedding"]:
            embedding = np.array(data["embedding"])
            
        entry = cls(
            key=data["key"],
            content=data["content"],
            memory_type=memory_type,
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
            last_accessed=last_accessed,
            access_count=data.get("access_count", 1),
            importance=data.get("importance", 1.0)
        )
        
        # Set ID if provided
        if "id" in data:
            entry.id = data["id"]
            
        return entry


class MemoryStore:
    """
    Persistent memory storage using SQLite with async support
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("memory_store.db")
        self.connection: Optional[aiosqlite.Connection] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database and create tables"""
        if self._initialized:
            return
            
        # Create database directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.connection = await aiosqlite.connect(str(self.db_path))
        
        # Enable foreign keys
        await self.connection.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        await self._create_tables()
        
        self._initialized = True
        logger.info(f"Memory store initialized at {self.db_path}")
        
    async def _create_tables(self):
        """Create database tables"""
        # Main memory table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 1,
                importance REAL DEFAULT 1.0,
                UNIQUE(key, memory_type)
            )
        """)
        
        # Indices for efficient querying
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_key ON memories(key)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_importance ON memories(importance DESC)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memories(last_accessed DESC)
        """)
        
        # Memory associations table for relationships
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS memory_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                association_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, association_type)
            )
        """)
        
        await self.connection.commit()
        
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store memory entry
        
        Args:
            entry: Memory entry to store
            
        Returns:
            Entry ID
        """
        if not self._initialized:
            await self.initialize()
            
        # Convert to storable format
        data = entry.to_dict()
        
        # Serialize complex types
        content_json = json.dumps(data["content"])
        metadata_json = json.dumps(data["metadata"])
        embedding_blob = data["embedding"].tobytes() if "embedding" in data and data["embedding"] else None
        
        # Insert or update
        await self.connection.execute("""
            INSERT OR REPLACE INTO memories (
                id, key, content, memory_type, embedding, metadata,
                created_at, updated_at, last_accessed, access_count, importance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.key,
            content_json,
            entry.memory_type.value,
            embedding_blob,
            metadata_json,
            entry.created_at.isoformat(),
            entry.updated_at.isoformat(),
            entry.last_accessed.isoformat(),
            entry.access_count,
            entry.importance
        ))
        
        await self.connection.commit()
        logger.debug(f"Stored memory: {entry.id}")
        
        return entry.id
        
    async def get(self, key: str, memory_type: Optional[MemoryType] = None) -> Optional[MemoryEntry]:
        """
        Get memory entry by key
        
        Args:
            key: Memory key
            memory_type: Optional memory type filter
            
        Returns:
            Memory entry if found
        """
        if not self._initialized:
            await self.initialize()
            
        query = "SELECT * FROM memories WHERE key = ?"
        params = [key]
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type.value)
            
        query += " ORDER BY importance DESC, last_accessed DESC LIMIT 1"
        
        async with self.connection.execute(query, params) as cursor:
            row = await cursor.fetchone()
            
        if row:
            return await self._row_to_entry(row)
            
        return None
        
    async def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get memory entry by ID"""
        if not self._initialized:
            await self.initialize()
            
        async with self.connection.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            return await self._row_to_entry(row)
            
        return None
        
    async def search_by_embedding(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        min_similarity: float = 0.5
    ) -> List[MemoryEntry]:
        """
        Search memories by embedding similarity
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum results
            memory_types: Filter by memory types
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of memory entries sorted by similarity
        """
        if not self._initialized:
            await self.initialize()
            
        # Build query
        query = "SELECT * FROM memories WHERE embedding IS NOT NULL"
        params = []
        
        if memory_types:
            placeholders = ",".join(["?"] * len(memory_types))
            query += f" AND memory_type IN ({placeholders})"
            params.extend([mt.value for mt in memory_types])
            
        # Get all memories with embeddings
        async with self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            
        # Calculate similarities
        results = []
        for row in rows:
            entry = await self._row_to_entry(row)
            if entry.embedding is not None:
                # Cosine similarity
                similarity = float(np.dot(query_embedding, entry.embedding) / 
                                 (np.linalg.norm(query_embedding) * np.linalg.norm(entry.embedding)))
                
                if similarity >= min_similarity:
                    results.append((entry, similarity))
                    
        # Sort by similarity and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in results[:limit]]
        
    async def search_by_type(
        self,
        memory_type: MemoryType,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """
        Search memories by type and optional key prefix
        
        Args:
            memory_type: Memory type to search
            prefix: Optional key prefix
            limit: Maximum results
            
        Returns:
            List of memory entries
        """
        if not self._initialized:
            await self.initialize()
            
        query = "SELECT * FROM memories WHERE memory_type = ?"
        params = [memory_type.value]
        
        if prefix:
            query += " AND key LIKE ?"
            params.append(f"{prefix}%")
            
        query += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)
        
        async with self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            
        return [await self._row_to_entry(row) for row in rows]
        
    async def update(self, entry: MemoryEntry):
        """Update existing memory entry"""
        entry.updated_at = datetime.utcnow()
        await self.store(entry)
        
    async def delete(self, memory_id: str) -> bool:
        """
        Delete memory entry
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deleted
        """
        if not self._initialized:
            await self.initialize()
            
        result = await self.connection.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,)
        )
        
        await self.connection.commit()
        return result.rowcount > 0
        
    async def add_association(
        self,
        source_id: str,
        target_id: str,
        association_type: str,
        strength: float = 1.0
    ):
        """
        Add association between memories
        
        Args:
            source_id: Source memory ID
            target_id: Target memory ID
            association_type: Type of association
            strength: Association strength
        """
        if not self._initialized:
            await self.initialize()
            
        await self.connection.execute("""
            INSERT OR REPLACE INTO memory_associations (
                source_id, target_id, association_type, strength, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            source_id,
            target_id,
            association_type,
            strength,
            datetime.utcnow().isoformat()
        ))
        
        await self.connection.commit()
        
    async def get_associations(
        self,
        memory_id: str,
        association_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get memory associations
        
        Args:
            memory_id: Memory ID
            association_type: Optional filter by type
            
        Returns:
            List of associations
        """
        if not self._initialized:
            await self.initialize()
            
        query = """
            SELECT * FROM memory_associations 
            WHERE source_id = ? OR target_id = ?
        """
        params = [memory_id, memory_id]
        
        if association_type:
            query += " AND association_type = ?"
            params.append(association_type)
            
        async with self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            
        associations = []
        for row in rows:
            associations.append({
                "id": row[0],
                "source_id": row[1],
                "target_id": row[2],
                "association_type": row[3],
                "strength": row[4],
                "created_at": row[5],
                "direction": "outgoing" if row[1] == memory_id else "incoming"
            })
            
        return associations
        
    async def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """
        Count memories
        
        Args:
            memory_type: Optional filter by type
            
        Returns:
            Memory count
        """
        if not self._initialized:
            await self.initialize()
            
        query = "SELECT COUNT(*) FROM memories"
        params = []
        
        if memory_type:
            query += " WHERE memory_type = ?"
            params.append(memory_type.value)
            
        async with self.connection.execute(query, params) as cursor:
            result = await cursor.fetchone()
            
        return result[0] if result else 0
        
    async def cleanup(
        self,
        max_age_days: int = 30,
        min_importance: float = 0.3,
        min_access_count: int = 2
    ) -> int:
        """
        Clean up old or unimportant memories
        
        Args:
            max_age_days: Maximum age in days
            min_importance: Minimum importance to keep
            min_access_count: Minimum access count to keep
            
        Returns:
            Number of memories deleted
        """
        if not self._initialized:
            await self.initialize()
            
        cutoff_date = datetime.utcnow().timestamp() - (max_age_days * 86400)
        
        result = await self.connection.execute("""
            DELETE FROM memories 
            WHERE memory_type = 'short_term'
            AND julianday('now') - julianday(last_accessed) > ?
            AND importance < ?
            AND access_count < ?
        """, (max_age_days, min_importance, min_access_count))
        
        await self.connection.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} old memories")
        
        return deleted_count
        
    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        if not self._initialized:
            await self.initialize()
            
        stats = {}
        
        # Count by type
        for memory_type in MemoryType:
            count = await self.count(memory_type)
            stats[f"count_{memory_type.value}"] = count
            
        # Total count
        stats["total_count"] = await self.count()
        
        # Average importance
        async with self.connection.execute(
            "SELECT AVG(importance) FROM memories"
        ) as cursor:
            result = await cursor.fetchone()
            stats["avg_importance"] = result[0] if result[0] else 0
            
        # Average access count
        async with self.connection.execute(
            "SELECT AVG(access_count) FROM memories"
        ) as cursor:
            result = await cursor.fetchone()
            stats["avg_access_count"] = result[0] if result[0] else 0
            
        # Association count
        async with self.connection.execute(
            "SELECT COUNT(*) FROM memory_associations"
        ) as cursor:
            result = await cursor.fetchone()
            stats["association_count"] = result[0] if result else 0
            
        return stats
        
    async def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert database row to MemoryEntry"""
        # Parse content and metadata
        content = json.loads(row[2])
        metadata = json.loads(row[5]) if row[5] else {}
        
        # Parse embedding
        embedding = None
        if row[4]:
            # Assuming embeddings are stored as float32
            embedding = np.frombuffer(row[4], dtype=np.float32)
            
        # Create entry
        entry = MemoryEntry(
            key=row[1],
            content=content,
            memory_type=MemoryType(row[3]),
            embedding=embedding,
            metadata=metadata,
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            last_accessed=datetime.fromisoformat(row[8]),
            access_count=row[9],
            importance=row[10]
        )
        
        # Set ID
        entry.id = row[0]
        
        return entry
        
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self._initialized = False
            logger.info("Memory store closed")