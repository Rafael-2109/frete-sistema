#!/usr/bin/env python3
"""
Session Migration Script
Migrates active sessions and conversation state from claude_ai_novo to MCP system

Features:
- Active session preservation
- Conversation context migration
- User session state transfer
- Session metadata preservation
- Context continuity maintenance
"""

import os
import sys
import json
import logging
import datetime
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiofiles
import uuid

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_sistema.models.database import DatabaseManager
from app.mcp_sistema.models.mcp_session import SessionManager, MCPSession
from app.mcp_sistema.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_sessions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SessionMigrationStats:
    """Statistics for session migration"""
    sessions_migrated: int = 0
    conversations_migrated: int = 0
    context_items_migrated: int = 0
    user_sessions_migrated: int = 0
    active_sessions_preserved: int = 0
    historical_sessions_archived: int = 0
    total_size_mb: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class SessionMigrator:
    """Main class for session data migration"""
    
    def __init__(self, source_path: str = None, target_db_url: str = None):
        """
        Initialize session migrator
        
        Args:
            source_path: Path to claude_ai_novo session data
            target_db_url: Target MCP database URL
        """
        self.source_path = Path(source_path) if source_path else Path("app/claude_ai_novo")
        self.target_db_url = target_db_url
        self.stats = SessionMigrationStats()
        self.config = load_config()
        self.db_manager = None
        self.session_manager = None
        
        # Session source mappings
        self.session_sources = {
            "conversation_memory.py": "conversation_sessions",
            "session_memory.py": "session_data",
            "context_memory.py": "context_sessions",
            "system_memory.py": "system_sessions"
        }
        
        # User mapping for sessions
        self.user_mapping = {}
        self.session_mapping = {}
        
        logger.info(f"Initialized session migrator: {self.source_path} -> MCP System")
    
    async def initialize(self):
        """Initialize database connections and managers"""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.target_db_url or self.config.database.url)
            await self.db_manager.initialize()
            
            # Initialize session manager
            self.session_manager = SessionManager(self.db_manager)
            
            logger.info("Session migration system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize session migration: {e}")
            self.stats.errors.append(f"Initialization error: {e}")
            return False
    
    async def analyze_session_sources(self) -> Dict[str, Any]:
        """Analyze available session sources"""
        analysis = {
            "session_files": [],
            "conversation_files": [],
            "context_files": [],
            "memory_files": [],
            "total_size_mb": 0,
            "session_types": {
                "conversation": 0,
                "context": 0,
                "system": 0,
                "user": 0
            },
            "estimated_sessions": 0,
            "active_sessions": 0,
            "date_range": {
                "earliest": None,
                "latest": None
            }
        }
        
        try:
            if not self.source_path.exists():
                logger.warning(f"Source path does not exist: {self.source_path}")
                return analysis
            
            # Look for session data sources
            session_dirs = [
                self.source_path / "memorizers",
                self.source_path / "conversers",
                self.source_path / "processors",
                Path("memory/sessions"),
                Path("logs")
            ]
            
            session_patterns = [
                "*session*.json",
                "*conversation*.json", 
                "*context*.json",
                "*memory*.json",
                "*.log"
            ]
            
            for session_dir in session_dirs:
                if session_dir.exists():
                    for pattern in session_patterns:
                        files = list(session_dir.glob(pattern))
                        
                        for file_path in files:
                            if file_path.is_file():
                                size_mb = file_path.stat().st_size / (1024 * 1024)
                                analysis["total_size_mb"] += size_mb
                                
                                file_info = await self._analyze_session_file(file_path)
                                if file_info:
                                    # Categorize by content type
                                    if "conversation" in file_path.name.lower():
                                        analysis["conversation_files"].append(file_info)
                                        analysis["session_types"]["conversation"] += 1
                                    elif "context" in file_path.name.lower():
                                        analysis["context_files"].append(file_info)
                                        analysis["session_types"]["context"] += 1
                                    elif "session" in file_path.name.lower():
                                        analysis["session_files"].append(file_info)
                                        analysis["session_types"]["user"] += 1
                                    elif "memory" in file_path.name.lower():
                                        analysis["memory_files"].append(file_info)
                                        analysis["session_types"]["system"] += 1
                                    
                                    # Update date range
                                    file_date = file_info.get("last_modified")
                                    if file_date:
                                        if not analysis["date_range"]["earliest"] or file_date < analysis["date_range"]["earliest"]:
                                            analysis["date_range"]["earliest"] = file_date
                                        if not analysis["date_range"]["latest"] or file_date > analysis["date_range"]["latest"]:
                                            analysis["date_range"]["latest"] = file_date
                                    
                                    # Estimate sessions
                                    estimated = file_info.get("estimated_sessions", 0)
                                    analysis["estimated_sessions"] += estimated
                                    
                                    # Check for active sessions
                                    if file_info.get("contains_active_sessions", False):
                                        analysis["active_sessions"] += estimated
            
            logger.info(f"Session analysis complete: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing session sources: {e}")
            self.stats.errors.append(f"Session analysis error: {e}")
            return analysis
    
    async def _analyze_session_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze individual session file"""
        try:
            file_info = {
                "path": str(file_path),
                "size_mb": file_path.stat().st_size / (1024 * 1024),
                "type": file_path.suffix,
                "module": file_path.parent.name,
                "last_modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime),
                "estimated_sessions": 0,
                "contains_active_sessions": False
            }
            
            # Try to analyze content for session estimation
            if file_path.suffix == ".json":
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    
                    data = json.loads(content)
                    
                    # Estimate sessions based on data structure
                    if isinstance(data, list):
                        file_info["estimated_sessions"] = len(data)
                    elif isinstance(data, dict):
                        if "sessions" in data:
                            file_info["estimated_sessions"] = len(data["sessions"]) if isinstance(data["sessions"], list) else 1
                        elif "conversations" in data:
                            file_info["estimated_sessions"] = len(data["conversations"]) if isinstance(data["conversations"], list) else 1
                        else:
                            file_info["estimated_sessions"] = 1
                    
                    # Check for recent activity (active sessions)
                    now = datetime.datetime.now()
                    if file_info["last_modified"] > now - datetime.timedelta(hours=24):
                        file_info["contains_active_sessions"] = True
                        
                except Exception:
                    # If we can't parse, just use file presence
                    file_info["estimated_sessions"] = 1
            
            elif file_path.suffix == ".log":
                # For log files, estimate based on size (rough heuristic)
                file_info["estimated_sessions"] = max(1, int(file_info["size_mb"] * 10))  # Rough estimate
            
            return file_info
            
        except Exception as e:
            logger.warning(f"Could not analyze session file {file_path}: {e}")
            return None
    
    async def migrate_conversation_sessions(self) -> bool:
        """Migrate conversation session data"""
        try:
            logger.info("Starting conversation sessions migration...")
            
            # Find conversation data
            conversation_sources = []
            
            conversation_dirs = [
                self.source_path / "conversers",
                self.source_path / "memorizers",
                Path("memory/sessions")
            ]
            
            for conv_dir in conversation_dirs:
                if conv_dir.exists():
                    conversation_sources.extend(list(conv_dir.glob("*conversation*.json")))
                    conversation_sources.extend(list(conv_dir.glob("*context*.json")))
            
            for conv_file in conversation_sources:
                try:
                    await self._migrate_conversation_file(conv_file)
                except Exception as e:
                    logger.error(f"Error migrating conversation file {conv_file}: {e}")
                    self.stats.errors.append(f"Conversation file error: {conv_file} - {e}")
            
            logger.info("Conversation sessions migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Conversation sessions migration failed: {e}")
            self.stats.errors.append(f"Conversation sessions migration error: {e}")
            return False
    
    async def _migrate_conversation_file(self, conv_file: Path):
        """Migrate individual conversation file"""
        try:
            # Read conversation data
            async with aiofiles.open(conv_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            conversation_data = json.loads(content)
            
            # Process based on data structure
            if isinstance(conversation_data, list):
                # List of conversations
                for i, conversation in enumerate(conversation_data):
                    await self._create_conversation_session(conversation, f"{conv_file.stem}_{i}")
            
            elif isinstance(conversation_data, dict):
                if "conversations" in conversation_data:
                    # Dictionary with conversations array
                    for i, conversation in enumerate(conversation_data["conversations"]):
                        await self._create_conversation_session(conversation, f"{conv_file.stem}_{i}")
                else:
                    # Single conversation object
                    await self._create_conversation_session(conversation_data, conv_file.stem)
            
            logger.debug(f"Migrated conversation file: {conv_file}")
            
        except Exception as e:
            logger.error(f"Error migrating conversation file {conv_file}: {e}")
            raise
    
    async def _create_conversation_session(self, conversation_data: Dict[str, Any], identifier: str):
        """Create MCP session from conversation data"""
        try:
            # Generate session ID
            session_id = f"migrated_conversation_{identifier}_{uuid.uuid4().hex[:8]}"
            
            # Extract user info
            user_id = conversation_data.get("user_id", "migrated_user")
            
            # Build session context
            context = {
                "conversation_data": conversation_data,
                "source": "claude_ai_novo",
                "migration_timestamp": datetime.datetime.utcnow().isoformat(),
                "type": "conversation",
                "messages": conversation_data.get("messages", []),
                "history": conversation_data.get("history", [])
            }
            
            # Build metadata
            metadata = {
                "migrated": True,
                "source_system": "claude_ai_novo",
                "migration_date": datetime.datetime.utcnow().isoformat(),
                "conversation_id": conversation_data.get("id", identifier),
                "user_agent": conversation_data.get("user_agent", "unknown"),
                "session_type": "conversation",
                "message_count": len(conversation_data.get("messages", [])),
                "last_activity": conversation_data.get("last_activity", datetime.datetime.utcnow().isoformat())
            }
            
            # Create session
            await self.session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                context=context,
                metadata=metadata
            )
            
            # Track mapping
            original_id = conversation_data.get("id", identifier)
            self.session_mapping[original_id] = session_id
            
            self.stats.conversations_migrated += 1
            logger.debug(f"Created conversation session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error creating conversation session: {e}")
            raise
    
    async def migrate_user_sessions(self) -> bool:
        """Migrate user session data"""
        try:
            logger.info("Starting user sessions migration...")
            
            # Find user session data
            session_sources = []
            
            session_dirs = [
                self.source_path / "memorizers",
                Path("memory/sessions"),
                Path("flask_session")
            ]
            
            for session_dir in session_dirs:
                if session_dir.exists():
                    session_sources.extend(list(session_dir.glob("*session*.json")))
                    session_sources.extend(list(session_dir.glob("*user*.json")))
            
            for session_file in session_sources:
                try:
                    await self._migrate_user_session_file(session_file)
                except Exception as e:
                    logger.error(f"Error migrating user session file {session_file}: {e}")
                    self.stats.errors.append(f"User session file error: {session_file} - {e}")
            
            logger.info("User sessions migration complete")
            return True
            
        except Exception as e:
            logger.error(f"User sessions migration failed: {e}")
            self.stats.errors.append(f"User sessions migration error: {e}")
            return False
    
    async def _migrate_user_session_file(self, session_file: Path):
        """Migrate individual user session file"""
        try:
            # Read session data
            async with aiofiles.open(session_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            session_data = json.loads(content)
            
            # Process based on data structure
            if isinstance(session_data, list):
                # List of sessions
                for i, session in enumerate(session_data):
                    await self._create_user_session(session, f"{session_file.stem}_{i}")
            
            elif isinstance(session_data, dict):
                if "sessions" in session_data:
                    # Dictionary with sessions array
                    for i, session in enumerate(session_data["sessions"]):
                        await self._create_user_session(session, f"{session_file.stem}_{i}")
                else:
                    # Single session object
                    await self._create_user_session(session_data, session_file.stem)
            
            logger.debug(f"Migrated user session file: {session_file}")
            
        except Exception as e:
            logger.error(f"Error migrating user session file {session_file}: {e}")
            raise
    
    async def _create_user_session(self, session_data: Dict[str, Any], identifier: str):
        """Create MCP session from user session data"""
        try:
            # Generate session ID
            session_id = f"migrated_user_{identifier}_{uuid.uuid4().hex[:8]}"
            
            # Extract user info
            user_id = session_data.get("user_id", session_data.get("id", "migrated_user"))
            
            # Build session context
            context = {
                "user_session_data": session_data,
                "source": "claude_ai_novo",
                "migration_timestamp": datetime.datetime.utcnow().isoformat(),
                "type": "user_session",
                "preferences": session_data.get("preferences", {}),
                "settings": session_data.get("settings", {}),
                "state": session_data.get("state", {})
            }
            
            # Build metadata
            metadata = {
                "migrated": True,
                "source_system": "claude_ai_novo",
                "migration_date": datetime.datetime.utcnow().isoformat(),
                "original_session_id": session_data.get("session_id", identifier),
                "session_type": "user_session",
                "login_time": session_data.get("login_time", datetime.datetime.utcnow().isoformat()),
                "last_seen": session_data.get("last_seen", datetime.datetime.utcnow().isoformat()),
                "ip_address": session_data.get("ip_address", "unknown"),
                "user_agent": session_data.get("user_agent", "unknown")
            }
            
            # Check if session is still active (within last 24 hours)
            last_seen = session_data.get("last_seen")
            if last_seen:
                try:
                    last_seen_dt = datetime.datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    if datetime.datetime.now(last_seen_dt.tzinfo) - last_seen_dt < datetime.timedelta(hours=24):
                        metadata["active_session"] = True
                        self.stats.active_sessions_preserved += 1
                    else:
                        metadata["active_session"] = False
                        self.stats.historical_sessions_archived += 1
                except:
                    metadata["active_session"] = False
            
            # Create session
            await self.session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                context=context,
                metadata=metadata
            )
            
            # Track user mapping
            if user_id not in self.user_mapping:
                self.user_mapping[user_id] = []
            self.user_mapping[user_id].append(session_id)
            
            self.stats.user_sessions_migrated += 1
            logger.debug(f"Created user session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error creating user session: {e}")
            raise
    
    async def migrate_context_data(self) -> bool:
        """Migrate context and memory data"""
        try:
            logger.info("Starting context data migration...")
            
            # Find context data
            context_sources = []
            
            context_dirs = [
                self.source_path / "memorizers",
                self.source_path / "loaders",
                self.source_path / "providers"
            ]
            
            for context_dir in context_dirs:
                if context_dir.exists():
                    context_sources.extend(list(context_dir.glob("*context*.json")))
                    context_sources.extend(list(context_dir.glob("*memory*.json")))
            
            for context_file in context_sources:
                try:
                    await self._migrate_context_file(context_file)
                except Exception as e:
                    logger.error(f"Error migrating context file {context_file}: {e}")
                    self.stats.errors.append(f"Context file error: {context_file} - {e}")
            
            logger.info("Context data migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Context data migration failed: {e}")
            self.stats.errors.append(f"Context data migration error: {e}")
            return False
    
    async def _migrate_context_file(self, context_file: Path):
        """Migrate individual context file"""
        try:
            # Read context data
            async with aiofiles.open(context_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            context_data = json.loads(content)
            
            # Process based on data structure
            if isinstance(context_data, list):
                # List of context items
                for i, context_item in enumerate(context_data):
                    await self._create_context_session(context_item, f"{context_file.stem}_{i}")
            
            elif isinstance(context_data, dict):
                if "contexts" in context_data:
                    # Dictionary with contexts array
                    for i, context_item in enumerate(context_data["contexts"]):
                        await self._create_context_session(context_item, f"{context_file.stem}_{i}")
                else:
                    # Single context object
                    await self._create_context_session(context_data, context_file.stem)
            
            logger.debug(f"Migrated context file: {context_file}")
            
        except Exception as e:
            logger.error(f"Error migrating context file {context_file}: {e}")
            raise
    
    async def _create_context_session(self, context_data: Dict[str, Any], identifier: str):
        """Create MCP session from context data"""
        try:
            # Generate session ID
            session_id = f"migrated_context_{identifier}_{uuid.uuid4().hex[:8]}"
            
            # Extract user info
            user_id = context_data.get("user_id", "system")
            
            # Build session context
            context = {
                "context_data": context_data,
                "source": "claude_ai_novo",
                "migration_timestamp": datetime.datetime.utcnow().isoformat(),
                "type": "context_memory",
                "variables": context_data.get("variables", {}),
                "state": context_data.get("state", {}),
                "cache": context_data.get("cache", {})
            }
            
            # Build metadata
            metadata = {
                "migrated": True,
                "source_system": "claude_ai_novo",
                "migration_date": datetime.datetime.utcnow().isoformat(),
                "context_id": context_data.get("id", identifier),
                "session_type": "context_memory",
                "scope": context_data.get("scope", "global"),
                "ttl": context_data.get("ttl"),
                "priority": context_data.get("priority", "normal")
            }
            
            # Create session
            await self.session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                context=context,
                metadata=metadata
            )
            
            self.stats.context_items_migrated += 1
            logger.debug(f"Created context session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error creating context session: {e}")
            raise
    
    async def create_migration_summary(self) -> Dict[str, Any]:
        """Create session migration summary"""
        summary = {
            "migration_timestamp": datetime.datetime.utcnow().isoformat(),
            "source_path": str(self.source_path),
            "target_system": "MCP Sistema",
            "statistics": asdict(self.stats),
            "success": len(self.stats.errors) == 0,
            "session_mappings": {
                "user_mappings": self.user_mapping,
                "session_mappings": self.session_mapping
            },
            "migration_types": {
                "conversation_sessions": "Conversation history and context",
                "user_sessions": "User authentication and preferences",
                "context_sessions": "System context and memory data"
            },
            "recommendations": []
        }
        
        # Add recommendations
        if self.stats.sessions_migrated > 0:
            summary["recommendations"].append(
                "Verify migrated sessions are accessible through MCP session API"
            )
        
        if self.stats.active_sessions_preserved > 0:
            summary["recommendations"].append(
                f"Update active user sessions ({self.stats.active_sessions_preserved}) to use new MCP session management"
            )
        
        if self.stats.conversations_migrated > 0:
            summary["recommendations"].append(
                "Test conversation continuity with migrated conversation sessions"
            )
        
        if self.stats.context_items_migrated > 0:
            summary["recommendations"].append(
                "Verify context data integrity and update context access patterns"
            )
        
        if self.stats.errors:
            summary["recommendations"].append(
                "Review migration errors and consider manual intervention for failed sessions"
            )
        
        return summary
    
    async def run_migration(self) -> Dict[str, Any]:
        """Run complete session migration"""
        logger.info("=== Starting Session Migration ===")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return {"success": False, "error": "Failed to initialize"}
            
            # Analyze session sources
            analysis = await self.analyze_session_sources()
            logger.info(f"Session analysis: {analysis}")
            
            # Run migrations
            migration_tasks = [
                self.migrate_conversation_sessions(),
                self.migrate_user_sessions(),
                self.migrate_context_data()
            ]
            
            results = await asyncio.gather(*migration_tasks, return_exceptions=True)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Session migration task {i} failed: {result}")
                    self.stats.errors.append(f"Task {i} failed: {result}")
            
            # Update total sessions migrated
            self.stats.sessions_migrated = (
                self.stats.conversations_migrated +
                self.stats.user_sessions_migrated +
                self.stats.context_items_migrated
            )
            
            # Create summary
            summary = await self.create_migration_summary()
            
            # Save summary
            summary_path = Path("migration_summary_sessions.json")
            async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, default=str))
            
            logger.info(f"Session migration complete! Summary: {summary_path}")
            logger.info(f"Statistics: {self.stats}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Session migration failed: {e}")
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
    """Main session migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate sessions from claude_ai_novo to MCP system")
    parser.add_argument("--source", help="Source session data path")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, no migration")
    
    args = parser.parse_args()
    
    migrator = SessionMigrator(
        source_path=args.source,
        target_db_url=args.target_db
    )
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        analysis = await migrator.analyze_session_sources()
        print(json.dumps(analysis, indent=2, default=str))
    else:
        result = await migrator.run_migration()
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())