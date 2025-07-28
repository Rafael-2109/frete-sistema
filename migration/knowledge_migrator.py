#!/usr/bin/env python3
"""
Knowledge Base Migration Script
Migrates knowledge base data from claude_ai_novo to MCP system

Features:
- Knowledge base content migration
- Semantic mapping preservation
- Learning patterns transfer
- Memory system migration
- Context preservation
"""

import os
import sys
import json
import sqlite3
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiofiles
import pickle
import hashlib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_sistema.models.database import DatabaseManager
from app.mcp_sistema.models.mcp_models import MCPResource
from app.mcp_sistema.services.mcp.resources import ResourceManager
from app.mcp_sistema.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_knowledge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeMigrationStats:
    """Statistics for knowledge migration"""
    knowledge_items_migrated: int = 0
    semantic_mappings_migrated: int = 0
    learning_patterns_migrated: int = 0
    memory_entries_migrated: int = 0
    context_items_migrated: int = 0
    databases_processed: int = 0
    total_size_mb: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class KnowledgeBaseMigrator:
    """Main class for knowledge base migration"""
    
    def __init__(self, source_path: str = None, target_db_url: str = None):
        """
        Initialize knowledge base migrator
        
        Args:
            source_path: Path to claude_ai_novo knowledge data
            target_db_url: Target MCP database URL
        """
        self.source_path = Path(source_path) if source_path else Path("app/claude_ai_novo")
        self.target_db_url = target_db_url
        self.stats = KnowledgeMigrationStats()
        self.config = load_config()
        self.db_manager = None
        self.resource_manager = None
        
        # Knowledge source mappings
        self.knowledge_sources = {
            "knowledge_base.sql": "sql_knowledge",
            "semantic_mapping.json": "semantic_mappings", 
            "mapeamento_semantico.py": "semantic_code",
            "memory": "memory_data",
            "learning": "learning_patterns",
            "context": "context_data"
        }
        
        logger.info(f"Initialized knowledge migrator: {self.source_path} -> MCP System")
    
    async def initialize(self):
        """Initialize database connections and managers"""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.target_db_url or self.config.database.url)
            await self.db_manager.initialize()
            
            # Initialize resource manager
            self.resource_manager = ResourceManager(self.db_manager)
            
            logger.info("Knowledge migration system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge migration: {e}")
            self.stats.errors.append(f"Initialization error: {e}")
            return False
    
    async def analyze_knowledge_sources(self) -> Dict[str, Any]:
        """Analyze available knowledge sources"""
        analysis = {
            "knowledge_databases": [],
            "semantic_mappings": [],
            "learning_data": [],
            "memory_stores": [],
            "context_data": [],
            "total_size_mb": 0,
            "source_types": {
                "sql": 0,
                "json": 0,
                "python": 0,
                "pickle": 0,
                "sqlite": 0
            },
            "estimated_items": 0
        }
        
        try:
            if not self.source_path.exists():
                logger.warning(f"Source path does not exist: {self.source_path}")
                return analysis
            
            # Scan for knowledge files
            knowledge_patterns = [
                "*knowledge*.sql",
                "*knowledge*.db",
                "*knowledge*.sqlite",
                "*semantic*.json",
                "*semantic*.py",
                "*mapping*.json",
                "*memory*.json",
                "*memory*.db",
                "*learning*.json",
                "*context*.json",
                "*.pkl",
                "*.pickle"
            ]
            
            for pattern in knowledge_patterns:
                files = list(self.source_path.rglob(pattern))
                
                for file_path in files:
                    if file_path.is_file():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        analysis["total_size_mb"] += size_mb
                        
                        file_info = {
                            "path": str(file_path),
                            "size_mb": size_mb,
                            "type": file_path.suffix,
                            "module": file_path.parent.name,
                            "last_modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                        }
                        
                        # Categorize by content type
                        if "knowledge" in file_path.name.lower():
                            analysis["knowledge_databases"].append(file_info)
                            if file_path.suffix in [".db", ".sqlite"]:
                                analysis["source_types"]["sqlite"] += 1
                                # Estimate items in SQLite
                                estimated = await self._estimate_sqlite_items(file_path)
                                analysis["estimated_items"] += estimated
                            elif file_path.suffix == ".sql":
                                analysis["source_types"]["sql"] += 1
                        
                        elif "semantic" in file_path.name.lower() or "mapping" in file_path.name.lower():
                            analysis["semantic_mappings"].append(file_info)
                            if file_path.suffix == ".json":
                                analysis["source_types"]["json"] += 1
                            elif file_path.suffix == ".py":
                                analysis["source_types"]["python"] += 1
                        
                        elif "learning" in file_path.name.lower():
                            analysis["learning_data"].append(file_info)
                            analysis["source_types"]["json"] += 1
                        
                        elif "memory" in file_path.name.lower():
                            analysis["memory_stores"].append(file_info)
                            if file_path.suffix in [".db", ".sqlite"]:
                                analysis["source_types"]["sqlite"] += 1
                            else:
                                analysis["source_types"]["json"] += 1
                        
                        elif "context" in file_path.name.lower():
                            analysis["context_data"].append(file_info)
                            analysis["source_types"]["json"] += 1
                        
                        elif file_path.suffix in [".pkl", ".pickle"]:
                            analysis["source_types"]["pickle"] += 1
            
            logger.info(f"Knowledge analysis complete: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing knowledge sources: {e}")
            self.stats.errors.append(f"Knowledge analysis error: {e}")
            return analysis
    
    async def _estimate_sqlite_items(self, db_path: Path) -> int:
        """Estimate number of items in SQLite database"""
        try:
            if not db_path.exists():
                return 0
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            total_items = 0
            try:
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                # Count items in each table
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    total_items += count
                
                return total_items
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.warning(f"Could not estimate items in {db_path}: {e}")
            return 0
    
    async def migrate_knowledge_databases(self) -> bool:
        """Migrate knowledge databases and SQL files"""
        try:
            logger.info("Starting knowledge database migration...")
            
            # Find knowledge database files
            db_files = []
            db_files.extend(list(self.source_path.rglob("*knowledge*.db")))
            db_files.extend(list(self.source_path.rglob("*knowledge*.sqlite")))
            db_files.extend(list(self.source_path.rglob("*knowledge*.sql")))
            
            for db_file in db_files:
                try:
                    await self._migrate_knowledge_database(db_file)
                except Exception as e:
                    logger.error(f"Error migrating knowledge database {db_file}: {e}")
                    self.stats.errors.append(f"Knowledge DB error: {db_file} - {e}")
            
            logger.info("Knowledge database migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Knowledge database migration failed: {e}")
            self.stats.errors.append(f"Knowledge DB migration error: {e}")
            return False
    
    async def _migrate_knowledge_database(self, db_file: Path):
        """Migrate individual knowledge database"""
        try:
            if db_file.suffix == ".sql":
                await self._migrate_sql_knowledge(db_file)
            elif db_file.suffix in [".db", ".sqlite"]:
                await self._migrate_sqlite_knowledge(db_file)
            
            self.stats.databases_processed += 1
            
        except Exception as e:
            logger.error(f"Error migrating knowledge database {db_file}: {e}")
            raise
    
    async def _migrate_sql_knowledge(self, sql_file: Path):
        """Migrate SQL knowledge file"""
        try:
            # Read SQL content
            async with aiofiles.open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = await f.read()
            
            # Parse SQL statements and extract knowledge
            knowledge_items = self._parse_sql_knowledge(sql_content)
            
            # Create MCP resources for each knowledge item
            for item in knowledge_items:
                await self._create_knowledge_resource(
                    uri=f"knowledge://sql/{item['id']}",
                    name=item['name'],
                    description=item['description'],
                    content=item['content'],
                    source_file=str(sql_file),
                    knowledge_type="sql_knowledge"
                )
            
            logger.debug(f"Migrated SQL knowledge: {sql_file} ({len(knowledge_items)} items)")
            
        except Exception as e:
            logger.error(f"Error migrating SQL knowledge {sql_file}: {e}")
            raise
    
    def _parse_sql_knowledge(self, sql_content: str) -> List[Dict[str, Any]]:
        """Parse SQL content to extract knowledge items"""
        knowledge_items = []
        
        try:
            # Split by statements
            statements = sql_content.split(';')
            
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if not statement:
                    continue
                
                # Extract knowledge from CREATE TABLE statements
                if statement.upper().startswith('CREATE TABLE'):
                    table_name = self._extract_table_name(statement)
                    knowledge_items.append({
                        "id": f"table_{table_name}_{i}",
                        "name": f"Table Schema: {table_name}",
                        "description": f"Database table schema for {table_name}",
                        "content": statement,
                        "type": "table_schema"
                    })
                
                # Extract knowledge from INSERT statements
                elif statement.upper().startswith('INSERT'):
                    table_name = self._extract_insert_table(statement)
                    knowledge_items.append({
                        "id": f"data_{table_name}_{i}",
                        "name": f"Data Insert: {table_name}",
                        "description": f"Data insertion for {table_name}",
                        "content": statement,
                        "type": "data_insert"
                    })
                
                # Extract other SQL knowledge
                else:
                    knowledge_items.append({
                        "id": f"sql_statement_{i}",
                        "name": f"SQL Statement {i+1}",
                        "description": "SQL statement from knowledge base",
                        "content": statement,
                        "type": "sql_statement"
                    })
            
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Error parsing SQL knowledge: {e}")
            return []
    
    def _extract_table_name(self, create_statement: str) -> str:
        """Extract table name from CREATE TABLE statement"""
        try:
            # Simple regex-like extraction
            parts = create_statement.split()
            for i, part in enumerate(parts):
                if part.upper() == "TABLE":
                    if i + 1 < len(parts):
                        return parts[i + 1].strip('(`)')
            return "unknown_table"
        except:
            return "unknown_table"
    
    def _extract_insert_table(self, insert_statement: str) -> str:
        """Extract table name from INSERT statement"""
        try:
            parts = insert_statement.split()
            for i, part in enumerate(parts):
                if part.upper() == "INTO":
                    if i + 1 < len(parts):
                        return parts[i + 1].strip('(`)')
            return "unknown_table"
        except:
            return "unknown_table"
    
    async def _migrate_sqlite_knowledge(self, db_file: Path):
        """Migrate SQLite knowledge database"""
        try:
            if not db_file.exists():
                return
            
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            
            try:
                # Get all tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Extract data from each table
                for table in tables:
                    cursor = conn.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    # Create knowledge resource for table data
                    table_data = [dict(row) for row in rows]
                    
                    await self._create_knowledge_resource(
                        uri=f"knowledge://sqlite/{db_file.stem}/{table}",
                        name=f"SQLite Table: {table}",
                        description=f"Data from SQLite table {table} in {db_file.name}",
                        content=json.dumps(table_data, indent=2),
                        source_file=str(db_file),
                        knowledge_type="sqlite_data",
                        metadata={"table": table, "row_count": len(table_data)}
                    )
                
                logger.debug(f"Migrated SQLite knowledge: {db_file} ({len(tables)} tables)")
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error migrating SQLite knowledge {db_file}: {e}")
            raise
    
    async def migrate_semantic_mappings(self) -> bool:
        """Migrate semantic mapping data"""
        try:
            logger.info("Starting semantic mappings migration...")
            
            # Find semantic mapping files
            mapping_files = []
            mapping_files.extend(list(self.source_path.rglob("*semantic*.json")))
            mapping_files.extend(list(self.source_path.rglob("*mapping*.json")))
            mapping_files.extend(list(self.source_path.rglob("*semantic*.py")))
            
            for mapping_file in mapping_files:
                try:
                    await self._migrate_semantic_mapping(mapping_file)
                except Exception as e:
                    logger.error(f"Error migrating semantic mapping {mapping_file}: {e}")
                    self.stats.errors.append(f"Semantic mapping error: {mapping_file} - {e}")
            
            logger.info("Semantic mappings migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Semantic mappings migration failed: {e}")
            self.stats.errors.append(f"Semantic mappings migration error: {e}")
            return False
    
    async def _migrate_semantic_mapping(self, mapping_file: Path):
        """Migrate individual semantic mapping file"""
        try:
            if mapping_file.suffix == ".json":
                await self._migrate_json_mapping(mapping_file)
            elif mapping_file.suffix == ".py":
                await self._migrate_python_mapping(mapping_file)
            
            self.stats.semantic_mappings_migrated += 1
            
        except Exception as e:
            logger.error(f"Error migrating semantic mapping {mapping_file}: {e}")
            raise
    
    async def _migrate_json_mapping(self, mapping_file: Path):
        """Migrate JSON semantic mapping"""
        try:
            # Read mapping data
            async with aiofiles.open(mapping_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            mapping_data = json.loads(content)
            
            # Create MCP resource for semantic mapping
            await self._create_knowledge_resource(
                uri=f"semantic://mapping/{mapping_file.stem}",
                name=f"Semantic Mapping: {mapping_file.stem}",
                description=f"Semantic mapping data from {mapping_file.name}",
                content=content,
                source_file=str(mapping_file),
                knowledge_type="semantic_mapping",
                metadata={"format": "json", "item_count": len(mapping_data) if isinstance(mapping_data, (list, dict)) else 1}
            )
            
            logger.debug(f"Migrated JSON semantic mapping: {mapping_file}")
            
        except Exception as e:
            logger.error(f"Error migrating JSON mapping {mapping_file}: {e}")
            raise
    
    async def _migrate_python_mapping(self, mapping_file: Path):
        """Migrate Python semantic mapping"""
        try:
            # Read Python code
            async with aiofiles.open(mapping_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Create MCP resource for Python mapping code
            await self._create_knowledge_resource(
                uri=f"semantic://code/{mapping_file.stem}",
                name=f"Semantic Code: {mapping_file.stem}",
                description=f"Semantic mapping code from {mapping_file.name}",
                content=content,
                source_file=str(mapping_file),
                knowledge_type="semantic_code",
                metadata={"format": "python", "language": "python"}
            )
            
            logger.debug(f"Migrated Python semantic mapping: {mapping_file}")
            
        except Exception as e:
            logger.error(f"Error migrating Python mapping {mapping_file}: {e}")
            raise
    
    async def migrate_learning_patterns(self) -> bool:
        """Migrate learning patterns and AI training data"""
        try:
            logger.info("Starting learning patterns migration...")
            
            # Find learning data files
            learning_dirs = [
                self.source_path / "learners",
                self.source_path / "learning",
                self.source_path / "training"
            ]
            
            learning_files = []
            for learning_dir in learning_dirs:
                if learning_dir.exists():
                    learning_files.extend(list(learning_dir.glob("*.json")))
                    learning_files.extend(list(learning_dir.glob("*.pkl")))
                    learning_files.extend(list(learning_dir.glob("*.pickle")))
            
            for learning_file in learning_files:
                try:
                    await self._migrate_learning_pattern(learning_file)
                except Exception as e:
                    logger.error(f"Error migrating learning pattern {learning_file}: {e}")
                    self.stats.errors.append(f"Learning pattern error: {learning_file} - {e}")
            
            logger.info("Learning patterns migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Learning patterns migration failed: {e}")
            self.stats.errors.append(f"Learning patterns migration error: {e}")
            return False
    
    async def _migrate_learning_pattern(self, learning_file: Path):
        """Migrate individual learning pattern file"""
        try:
            content = None
            metadata = {"format": learning_file.suffix}
            
            if learning_file.suffix == ".json":
                async with aiofiles.open(learning_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    metadata["content_type"] = "json"
            
            elif learning_file.suffix in [".pkl", ".pickle"]:
                # Handle pickle files carefully
                try:
                    with open(learning_file, 'rb') as f:
                        pickle_data = pickle.load(f)
                    content = json.dumps(pickle_data, default=str, indent=2)
                    metadata["content_type"] = "pickle_converted"
                except Exception as pickle_error:
                    logger.warning(f"Could not load pickle file {learning_file}: {pickle_error}")
                    # Read as binary and encode
                    with open(learning_file, 'rb') as f:
                        binary_data = f.read()
                    content = f"Binary data (base64): {binary_data.hex()}"
                    metadata["content_type"] = "binary"
            
            if content:
                await self._create_knowledge_resource(
                    uri=f"learning://pattern/{learning_file.stem}",
                    name=f"Learning Pattern: {learning_file.stem}",
                    description=f"Learning pattern from {learning_file.name}",
                    content=content,
                    source_file=str(learning_file),
                    knowledge_type="learning_pattern",
                    metadata=metadata
                )
            
            self.stats.learning_patterns_migrated += 1
            logger.debug(f"Migrated learning pattern: {learning_file}")
            
        except Exception as e:
            logger.error(f"Error migrating learning pattern {learning_file}: {e}")
            raise
    
    async def migrate_memory_data(self) -> bool:
        """Migrate memory system data"""
        try:
            logger.info("Starting memory data migration...")
            
            # Find memory data files
            memory_dirs = [
                self.source_path / "memorizers",
                self.source_path / "memory",
                Path("memory"),
                Path("memory/sessions")
            ]
            
            memory_files = []
            for memory_dir in memory_dirs:
                if memory_dir.exists():
                    memory_files.extend(list(memory_dir.glob("*.json")))
                    memory_files.extend(list(memory_dir.glob("*.db")))
                    memory_files.extend(list(memory_dir.glob("*.sqlite")))
            
            for memory_file in memory_files:
                try:
                    await self._migrate_memory_file(memory_file)
                except Exception as e:
                    logger.error(f"Error migrating memory file {memory_file}: {e}")
                    self.stats.errors.append(f"Memory file error: {memory_file} - {e}")
            
            logger.info("Memory data migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Memory data migration failed: {e}")
            self.stats.errors.append(f"Memory data migration error: {e}")
            return False
    
    async def _migrate_memory_file(self, memory_file: Path):
        """Migrate individual memory file"""
        try:
            if memory_file.suffix == ".json":
                await self._migrate_json_memory(memory_file)
            elif memory_file.suffix in [".db", ".sqlite"]:
                await self._migrate_sqlite_memory(memory_file)
            
            self.stats.memory_entries_migrated += 1
            
        except Exception as e:
            logger.error(f"Error migrating memory file {memory_file}: {e}")
            raise
    
    async def _migrate_json_memory(self, memory_file: Path):
        """Migrate JSON memory file"""
        try:
            # Read memory data
            async with aiofiles.open(memory_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Create MCP resource for memory data
            await self._create_knowledge_resource(
                uri=f"memory://data/{memory_file.stem}",
                name=f"Memory Data: {memory_file.stem}",
                description=f"Memory system data from {memory_file.name}",
                content=content,
                source_file=str(memory_file),
                knowledge_type="memory_data",
                metadata={"format": "json"}
            )
            
            logger.debug(f"Migrated JSON memory: {memory_file}")
            
        except Exception as e:
            logger.error(f"Error migrating JSON memory {memory_file}: {e}")
            raise
    
    async def _migrate_sqlite_memory(self, memory_file: Path):
        """Migrate SQLite memory file"""
        try:
            if not memory_file.exists():
                return
            
            conn = sqlite3.connect(str(memory_file))
            conn.row_factory = sqlite3.Row
            
            try:
                # Get all tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Extract memory data from each table
                for table in tables:
                    cursor = conn.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    # Create knowledge resource for memory table
                    memory_data = [dict(row) for row in rows]
                    
                    await self._create_knowledge_resource(
                        uri=f"memory://sqlite/{memory_file.stem}/{table}",
                        name=f"Memory Table: {table}",
                        description=f"Memory data from table {table} in {memory_file.name}",
                        content=json.dumps(memory_data, indent=2),
                        source_file=str(memory_file),
                        knowledge_type="memory_sqlite",
                        metadata={"table": table, "row_count": len(memory_data)}
                    )
                
                logger.debug(f"Migrated SQLite memory: {memory_file} ({len(tables)} tables)")
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error migrating SQLite memory {memory_file}: {e}")
            raise
    
    async def _create_knowledge_resource(self, uri: str, name: str, description: str, 
                                       content: str, source_file: str, knowledge_type: str,
                                       metadata: Dict[str, Any] = None):
        """Create MCP resource for knowledge item"""
        try:
            if metadata is None:
                metadata = {}
            
            # Add migration metadata
            metadata.update({
                "source": "claude_ai_novo",
                "migration_date": datetime.datetime.utcnow().isoformat(),
                "original_file": source_file,
                "knowledge_type": knowledge_type,
                "content_hash": hashlib.sha256(content.encode()).hexdigest()
            })
            
            # Calculate content size
            size_mb = len(content.encode()) / (1024 * 1024)
            self.stats.total_size_mb += size_mb
            
            # Create resource data
            resource_data = {
                "uri": uri,
                "name": name,
                "description": description,
                "mime_type": "application/json" if knowledge_type != "semantic_code" else "text/plain",
                "content": content,
                "metadata": metadata
            }
            
            # Store in MCP resources
            async with self.db_manager.get_session() as session:
                resource = MCPResource(**resource_data)
                session.add(resource)
                await session.commit()
            
            self.stats.knowledge_items_migrated += 1
            logger.debug(f"Created knowledge resource: {uri}")
            
        except Exception as e:
            logger.error(f"Error creating knowledge resource {uri}: {e}")
            raise
    
    async def create_migration_summary(self) -> Dict[str, Any]:
        """Create knowledge migration summary"""
        summary = {
            "migration_timestamp": datetime.datetime.utcnow().isoformat(),
            "source_path": str(self.source_path),
            "target_system": "MCP Sistema",
            "statistics": asdict(self.stats),
            "success": len(self.stats.errors) == 0,
            "knowledge_types_migrated": {
                "sql_knowledge": "Database schemas and queries",
                "sqlite_data": "SQLite database contents",
                "semantic_mapping": "Semantic mapping configurations",
                "semantic_code": "Python semantic mapping code",
                "learning_pattern": "AI learning patterns and training data",
                "memory_data": "Memory system data and context"
            },
            "recommendations": []
        }
        
        # Add recommendations
        if self.stats.knowledge_items_migrated > 0:
            summary["recommendations"].append(
                "Verify migrated knowledge items are accessible through MCP resources API"
            )
        
        if self.stats.semantic_mappings_migrated > 0:
            summary["recommendations"].append(
                "Integrate semantic mappings with MCP semantic processing capabilities"
            )
        
        if self.stats.learning_patterns_migrated > 0:
            summary["recommendations"].append(
                "Review learning patterns and adapt to new MCP learning systems"
            )
        
        if self.stats.memory_entries_migrated > 0:
            summary["recommendations"].append(
                "Update memory access patterns to use MCP memory management"
            )
        
        if self.stats.errors:
            summary["recommendations"].append(
                "Review migration errors and consider manual intervention for failed items"
            )
        
        return summary
    
    async def run_migration(self) -> Dict[str, Any]:
        """Run complete knowledge base migration"""
        logger.info("=== Starting Knowledge Base Migration ===")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return {"success": False, "error": "Failed to initialize"}
            
            # Analyze knowledge sources
            analysis = await self.analyze_knowledge_sources()
            logger.info(f"Knowledge analysis: {analysis}")
            
            # Run migrations
            migration_tasks = [
                self.migrate_knowledge_databases(),
                self.migrate_semantic_mappings(),
                self.migrate_learning_patterns(),
                self.migrate_memory_data()
            ]
            
            results = await asyncio.gather(*migration_tasks, return_exceptions=True)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Knowledge migration task {i} failed: {result}")
                    self.stats.errors.append(f"Task {i} failed: {result}")
            
            # Create summary
            summary = await self.create_migration_summary()
            
            # Save summary
            summary_path = Path("migration_summary_knowledge.json")
            async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, default=str))
            
            logger.info(f"Knowledge migration complete! Summary: {summary_path}")
            logger.info(f"Statistics: {self.stats}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Knowledge migration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "statistics": asdict(self.stats)
            }
        
        finally:
            # Cleanup
            if self.db_manager:
                await self.db_manager.close()

async def main():
    """Main knowledge migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate knowledge base from claude_ai_novo to MCP system")
    parser.add_argument("--source", help="Source knowledge path")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, no migration")
    
    args = parser.parse_args()
    
    migrator = KnowledgeBaseMigrator(
        source_path=args.source,
        target_db_url=args.target_db
    )
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        analysis = await migrator.analyze_knowledge_sources()
        print(json.dumps(analysis, indent=2, default=str))
    else:
        result = await migrator.run_migration()
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())