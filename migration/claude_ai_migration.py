#!/usr/bin/env python3
"""
Claude AI Data Migration Script
Transfers data and functionality from claude_ai_novo to MCP system

Migration Features:
- Conversation history preservation
- Learned patterns migration
- Configuration transfer
- Knowledge base migration
- Session state preservation
"""

import os
import sys
import json
import logging
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiofiles

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_sistema.models.database import DatabaseManager
from app.mcp_sistema.models.mcp_models import MCPSession, MCPLog, MCPResource
from app.mcp_sistema.models.mcp_session import SessionManager
from app.mcp_sistema.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_claude_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MigrationStats:
    """Statistics for migration tracking"""
    conversations_migrated: int = 0
    patterns_migrated: int = 0
    configs_migrated: int = 0
    knowledge_items_migrated: int = 0
    sessions_migrated: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class ClaudeAIDataMigrator:
    """Main migration class for Claude AI data transfer"""
    
    def __init__(self, source_path: str = None, target_db_url: str = None):
        """
        Initialize migrator
        
        Args:
            source_path: Path to claude_ai_novo data
            target_db_url: Target MCP database URL
        """
        self.source_path = Path(source_path) if source_path else Path("app/claude_ai_novo")
        self.target_db_url = target_db_url
        self.stats = MigrationStats()
        self.config = load_config()
        self.db_manager = None
        self.session_manager = None
        
        # Migration mappings
        self.conversation_mapping = {}
        self.user_mapping = {}
        self.context_mapping = {}
        
        logger.info(f"Initialized migrator: {self.source_path} -> MCP System")
    
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.target_db_url or self.config.database.url)
            await self.db_manager.initialize()
            
            # Initialize session manager
            self.session_manager = SessionManager(self.db_manager)
            
            logger.info("Database connections initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.stats.errors.append(f"Database initialization error: {e}")
            return False
    
    async def analyze_source_data(self) -> Dict[str, Any]:
        """Analyze source claude_ai_novo data"""
        analysis = {
            "total_modules": 0,
            "conversation_files": 0,
            "config_files": 0,
            "knowledge_files": 0,
            "session_files": 0,
            "data_size_mb": 0,
            "modules_found": [],
            "data_sources": {}
        }
        
        try:
            if not self.source_path.exists():
                logger.error(f"Source path does not exist: {self.source_path}")
                return analysis
            
            # Scan for data sources
            for item in self.source_path.rglob("*"):
                if item.is_file():
                    size_mb = item.stat().st_size / (1024 * 1024)
                    analysis["data_size_mb"] += size_mb
                    
                    # Categorize files
                    if "conversation" in item.name.lower():
                        analysis["conversation_files"] += 1
                    elif "config" in item.name.lower():
                        analysis["config_files"] += 1
                    elif "knowledge" in item.name.lower() or "memory" in item.name.lower():
                        analysis["knowledge_files"] += 1
                    elif "session" in item.name.lower():
                        analysis["session_files"] += 1
                    
                    # Track data sources
                    if item.suffix in ['.json', '.db', '.sqlite', '.sql']:
                        analysis["data_sources"][str(item)] = {
                            "size_mb": size_mb,
                            "type": item.suffix,
                            "last_modified": datetime.datetime.fromtimestamp(item.stat().st_mtime)
                        }
            
            # Count modules
            module_dirs = [d for d in self.source_path.iterdir() if d.is_dir() and d.name != "__pycache__"]
            analysis["total_modules"] = len(module_dirs)
            analysis["modules_found"] = [d.name for d in module_dirs]
            
            logger.info(f"Source analysis complete: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing source data: {e}")
            self.stats.errors.append(f"Source analysis error: {e}")
            return analysis
    
    async def migrate_conversations(self) -> bool:
        """Migrate conversation history"""
        try:
            logger.info("Starting conversation migration...")
            
            # Look for conversation data in various locations
            conversation_sources = []
            
            # Check for conversation memory files
            memory_dirs = [
                self.source_path / "memorizers",
                self.source_path / "memory",
                Path("memory/sessions"),
                Path("logs")
            ]
            
            for memory_dir in memory_dirs:
                if memory_dir.exists():
                    conversation_files = list(memory_dir.glob("*conversation*")) + list(memory_dir.glob("*session*"))
                    conversation_sources.extend(conversation_files)
            
            # Process each conversation source
            for source_file in conversation_sources:
                try:
                    await self._migrate_conversation_file(source_file)
                except Exception as e:
                    logger.error(f"Error migrating conversation file {source_file}: {e}")
                    self.stats.errors.append(f"Conversation file error: {source_file} - {e}")
            
            logger.info(f"Conversation migration complete: {self.stats.conversations_migrated} migrated")
            return True
            
        except Exception as e:
            logger.error(f"Conversation migration failed: {e}")
            self.stats.errors.append(f"Conversation migration error: {e}")
            return False
    
    async def _migrate_conversation_file(self, file_path: Path):
        """Migrate individual conversation file"""
        try:
            if not file_path.exists():
                return
            
            # Read conversation data
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse based on file type
            conversation_data = None
            if file_path.suffix == '.json':
                conversation_data = json.loads(content)
            elif file_path.suffix in ['.db', '.sqlite']:
                conversation_data = await self._extract_from_sqlite(file_path)
            else:
                # Plain text conversations
                conversation_data = {"content": content, "type": "text"}
            
            if not conversation_data:
                return
            
            # Create MCP session entry
            session_data = {
                "session_id": f"claude_ai_migration_{file_path.stem}",
                "user_id": "migrated_user",
                "context": {
                    "source": "claude_ai_novo",
                    "migration_timestamp": datetime.datetime.utcnow().isoformat(),
                    "original_file": str(file_path),
                    "data": conversation_data
                },
                "metadata": {
                    "migrated": True,
                    "source_system": "claude_ai_novo",
                    "migration_date": datetime.datetime.utcnow().isoformat()
                }
            }
            
            # Store in MCP session
            await self.session_manager.create_session(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                context=session_data["context"],
                metadata=session_data["metadata"]
            )
            
            self.stats.conversations_migrated += 1
            logger.debug(f"Migrated conversation: {file_path}")
            
        except Exception as e:
            logger.error(f"Error migrating conversation file {file_path}: {e}")
            raise
    
    async def migrate_learned_patterns(self) -> bool:
        """Migrate learned patterns and AI knowledge"""
        try:
            logger.info("Starting learned patterns migration...")
            
            pattern_sources = []
            
            # Look for pattern data
            pattern_dirs = [
                self.source_path / "learners",
                self.source_path / "analyzers",
                self.source_path / "suggestions",
                self.source_path / "processors"
            ]
            
            for pattern_dir in pattern_dirs:
                if pattern_dir.exists():
                    pattern_files = list(pattern_dir.glob("*.json")) + list(pattern_dir.glob("*.db"))
                    pattern_sources.extend(pattern_files)
            
            # Process pattern files
            for pattern_file in pattern_sources:
                try:
                    await self._migrate_pattern_file(pattern_file)
                except Exception as e:
                    logger.error(f"Error migrating pattern file {pattern_file}: {e}")
                    self.stats.errors.append(f"Pattern file error: {pattern_file} - {e}")
            
            logger.info(f"Patterns migration complete: {self.stats.patterns_migrated} migrated")
            return True
            
        except Exception as e:
            logger.error(f"Patterns migration failed: {e}")
            self.stats.errors.append(f"Patterns migration error: {e}")
            return False
    
    async def _migrate_pattern_file(self, file_path: Path):
        """Migrate individual pattern file"""
        try:
            if not file_path.exists():
                return
            
            # Read pattern data
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            pattern_data = None
            if file_path.suffix == '.json':
                pattern_data = json.loads(content)
            elif file_path.suffix in ['.db', '.sqlite']:
                pattern_data = await self._extract_from_sqlite(file_path)
            
            if not pattern_data:
                return
            
            # Create MCP resource for pattern
            resource_data = {
                "uri": f"pattern://claude_ai_novo/{file_path.stem}",
                "name": f"Migrated Pattern: {file_path.stem}",
                "description": f"Learned pattern migrated from claude_ai_novo: {file_path.name}",
                "mime_type": "application/json",
                "content": json.dumps(pattern_data),
                "metadata": {
                    "source": "claude_ai_novo",
                    "type": "learned_pattern",
                    "original_file": str(file_path),
                    "migration_date": datetime.datetime.utcnow().isoformat(),
                    "module": file_path.parent.name
                }
            }
            
            # Store in MCP resources
            async with self.db_manager.get_session() as session:
                resource = MCPResource(**resource_data)
                session.add(resource)
                await session.commit()
            
            self.stats.patterns_migrated += 1
            logger.debug(f"Migrated pattern: {file_path}")
            
        except Exception as e:
            logger.error(f"Error migrating pattern file {file_path}: {e}")
            raise
    
    async def migrate_configurations(self) -> bool:
        """Migrate configuration files"""
        try:
            logger.info("Starting configuration migration...")
            
            config_sources = []
            
            # Look for configuration files
            config_patterns = [
                "config*.json",
                "*_config.py",
                "settings*.json",
                "*.ini",
                "*.yaml",
                "*.yml"
            ]
            
            for pattern in config_patterns:
                config_files = list(self.source_path.rglob(pattern))
                config_sources.extend(config_files)
            
            # Process configuration files
            for config_file in config_sources:
                try:
                    await self._migrate_config_file(config_file)
                except Exception as e:
                    logger.error(f"Error migrating config file {config_file}: {e}")
                    self.stats.errors.append(f"Config file error: {config_file} - {e}")
            
            logger.info(f"Configuration migration complete: {self.stats.configs_migrated} migrated")
            return True
            
        except Exception as e:
            logger.error(f"Configuration migration failed: {e}")
            self.stats.errors.append(f"Configuration migration error: {e}")
            return False
    
    async def _migrate_config_file(self, file_path: Path):
        """Migrate individual configuration file"""
        try:
            if not file_path.exists():
                return
            
            # Read config data
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Create MCP resource for configuration
            resource_data = {
                "uri": f"config://claude_ai_novo/{file_path.stem}",
                "name": f"Migrated Config: {file_path.name}",
                "description": f"Configuration migrated from claude_ai_novo: {file_path.name}",
                "mime_type": "text/plain",
                "content": content,
                "metadata": {
                    "source": "claude_ai_novo",
                    "type": "configuration",
                    "original_file": str(file_path),
                    "migration_date": datetime.datetime.utcnow().isoformat(),
                    "module": file_path.parent.name,
                    "file_type": file_path.suffix
                }
            }
            
            # Store in MCP resources
            async with self.db_manager.get_session() as session:
                resource = MCPResource(**resource_data)
                session.add(resource)
                await session.commit()
            
            self.stats.configs_migrated += 1
            logger.debug(f"Migrated config: {file_path}")
            
        except Exception as e:
            logger.error(f"Error migrating config file {file_path}: {e}")
            raise
    
    async def _extract_from_sqlite(self, db_path: Path) -> Dict[str, Any]:
        """Extract data from SQLite database"""
        try:
            if not db_path.exists():
                return {}
            
            data = {}
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                # Get all tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Extract data from each table
                for table in tables:
                    cursor = conn.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    data[table] = [dict(row) for row in rows]
                
                return data
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error extracting from SQLite {db_path}: {e}")
            return {}
    
    async def create_migration_summary(self) -> Dict[str, Any]:
        """Create migration summary report"""
        summary = {
            "migration_timestamp": datetime.datetime.utcnow().isoformat(),
            "source_path": str(self.source_path),
            "target_system": "MCP Sistema",
            "statistics": asdict(self.stats),
            "success": len(self.stats.errors) == 0,
            "recommendations": []
        }
        
        # Add recommendations based on migration results
        if self.stats.conversations_migrated > 0:
            summary["recommendations"].append(
                "Verify migrated conversations are accessible through MCP session API"
            )
        
        if self.stats.patterns_migrated > 0:
            summary["recommendations"].append(
                "Review migrated patterns and integrate with new MCP learning systems"
            )
        
        if self.stats.configs_migrated > 0:
            summary["recommendations"].append(
                "Update configuration references in MCP system to use migrated configs"
            )
        
        if self.stats.errors:
            summary["recommendations"].append(
                "Review migration errors and consider manual intervention for failed items"
            )
        
        return summary
    
    async def run_migration(self) -> Dict[str, Any]:
        """Run complete migration process"""
        logger.info("=== Starting Claude AI Data Migration ===")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return {"success": False, "error": "Failed to initialize"}
            
            # Analyze source data
            analysis = await self.analyze_source_data()
            logger.info(f"Source analysis: {analysis}")
            
            # Run migrations
            migration_tasks = [
                self.migrate_conversations(),
                self.migrate_learned_patterns(),
                self.migrate_configurations()
            ]
            
            results = await asyncio.gather(*migration_tasks, return_exceptions=True)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Migration task {i} failed: {result}")
                    self.stats.errors.append(f"Task {i} failed: {result}")
            
            # Create summary
            summary = await self.create_migration_summary()
            
            # Save summary
            summary_path = Path("migration_summary_claude_ai.json")
            async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, default=str))
            
            logger.info(f"Migration complete! Summary saved to: {summary_path}")
            logger.info(f"Statistics: {self.stats}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
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
    """Main migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Claude AI data to MCP system")
    parser.add_argument("--source", help="Source claude_ai_novo path")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without actual migration")
    
    args = parser.parse_args()
    
    migrator = ClaudeAIDataMigrator(
        source_path=args.source,
        target_db_url=args.target_db
    )
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        analysis = await migrator.analyze_source_data()
        print(json.dumps(analysis, indent=2, default=str))
    else:
        result = await migrator.run_migration()
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())