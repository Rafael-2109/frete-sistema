#!/usr/bin/env python3
"""
Configuration Migration Script
Migrates configuration files and settings from claude_ai_novo to MCP system

Features:
- Configuration file mapping
- Environment variable migration
- Security settings transfer
- Module-specific configurations
- Backup and rollback support
"""

import os
import sys
import json
import yaml
import logging
import configparser
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import asyncio
import aiofiles
import shutil

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_sistema.config import load_config, MCPConfig, AppConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_config.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ConfigMigrationStats:
    """Statistics for configuration migration"""
    files_processed: int = 0
    configs_migrated: int = 0
    env_vars_migrated: int = 0
    security_settings_migrated: int = 0
    module_configs_migrated: int = 0
    backup_files_created: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class ConfigurationMigrator:
    """Main class for configuration migration"""
    
    def __init__(self, source_path: str = None, target_path: str = None):
        """
        Initialize configuration migrator
        
        Args:
            source_path: Path to claude_ai_novo configurations
            target_path: Path to MCP system configurations
        """
        self.source_path = Path(source_path) if source_path else Path("app/claude_ai_novo")
        self.target_path = Path(target_path) if target_path else Path("app/mcp_sistema")
        self.stats = ConfigMigrationStats()
        
        # Backup directory
        self.backup_dir = Path("migration/backups/config") / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration mappings
        self.config_mappings = {
            # Claude AI Novo -> MCP System mappings
            "advanced_config.py": "config.py",
            "basic_config.py": "core/settings.py",
            "development_config.json": "config/development.json",
            "global_config.json": "config/global.json",
            "system_config.py": "core/system.py",
            "security_config.json": "core/security.json"
        }
        
        # Environment variable mappings
        self.env_mappings = {
            "CLAUDE_AI_API_KEY": "MCP_CLAUDE_API_KEY",
            "CLAUDE_AI_MODEL": "MCP_AI_MODEL",
            "CLAUDE_AI_TIMEOUT": "MCP_TOOL_TIMEOUT",
            "CLAUDE_AI_MAX_TOKENS": "MCP_MAX_TOKENS",
            "CLAUDE_AI_TEMPERATURE": "MCP_TEMPERATURE",
            "CLAUDE_DATABASE_URL": "MCP_DATABASE_URL",
            "CLAUDE_REDIS_URL": "MCP_REDIS_URL",
            "CLAUDE_SECRET_KEY": "MCP_SECRET_KEY",
            "CLAUDE_DEBUG": "MCP_DEBUG"
        }
        
        logger.info(f"Initialized config migrator: {self.source_path} -> {self.target_path}")
    
    async def analyze_source_configs(self) -> Dict[str, Any]:
        """Analyze source configuration files"""
        analysis = {
            "config_files": [],
            "env_files": [],
            "module_configs": {},
            "security_configs": [],
            "total_size_mb": 0,
            "config_types": {
                "python": 0,
                "json": 0,
                "yaml": 0,
                "ini": 0,
                "env": 0
            }
        }
        
        try:
            if not self.source_path.exists():
                logger.warning(f"Source path does not exist: {self.source_path}")
                return analysis
            
            # Scan for configuration files
            config_patterns = [
                "*config*.py",
                "*config*.json",
                "*config*.yaml",
                "*config*.yml",
                "*.ini",
                ".env*",
                "*settings*.py",
                "*settings*.json"
            ]
            
            for pattern in config_patterns:
                config_files = list(self.source_path.rglob(pattern))
                
                for config_file in config_files:
                    if config_file.is_file():
                        size_mb = config_file.stat().st_size / (1024 * 1024)
                        analysis["total_size_mb"] += size_mb
                        
                        file_info = {
                            "path": str(config_file),
                            "size_mb": size_mb,
                            "type": config_file.suffix,
                            "module": config_file.parent.name,
                            "last_modified": datetime.datetime.fromtimestamp(config_file.stat().st_mtime)
                        }
                        
                        # Categorize by type
                        if config_file.suffix == ".py":
                            analysis["config_types"]["python"] += 1
                        elif config_file.suffix == ".json":
                            analysis["config_types"]["json"] += 1
                        elif config_file.suffix in [".yaml", ".yml"]:
                            analysis["config_types"]["yaml"] += 1
                        elif config_file.suffix == ".ini":
                            analysis["config_types"]["ini"] += 1
                        elif "env" in config_file.name:
                            analysis["config_types"]["env"] += 1
                            analysis["env_files"].append(file_info)
                        
                        # Check for security configs
                        if "security" in config_file.name.lower():
                            analysis["security_configs"].append(file_info)
                        
                        # Module-specific configs
                        module_name = config_file.parent.name
                        if module_name not in analysis["module_configs"]:
                            analysis["module_configs"][module_name] = []
                        analysis["module_configs"][module_name].append(file_info)
                        
                        analysis["config_files"].append(file_info)
            
            logger.info(f"Configuration analysis complete: {len(analysis['config_files'])} files found")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing source configs: {e}")
            self.stats.errors.append(f"Config analysis error: {e}")
            return analysis
    
    async def migrate_python_configs(self) -> bool:
        """Migrate Python configuration files"""
        try:
            logger.info("Starting Python configuration migration...")
            
            python_configs = list(self.source_path.rglob("*config*.py"))
            python_configs.extend(list(self.source_path.rglob("*settings*.py")))
            
            for config_file in python_configs:
                try:
                    await self._migrate_python_config(config_file)
                except Exception as e:
                    logger.error(f"Error migrating Python config {config_file}: {e}")
                    self.stats.errors.append(f"Python config error: {config_file} - {e}")
            
            logger.info("Python configuration migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Python config migration failed: {e}")
            self.stats.errors.append(f"Python config migration error: {e}")
            return False
    
    async def _migrate_python_config(self, config_file: Path):
        """Migrate individual Python configuration file"""
        try:
            # Read source file
            async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Create backup
            backup_path = self.backup_dir / config_file.name
            shutil.copy2(config_file, backup_path)
            self.stats.backup_files_created += 1
            
            # Determine target file
            target_file = self._get_target_config_path(config_file)
            
            # Transform content for MCP system
            transformed_content = self._transform_python_config(content, config_file.name)
            
            # Write transformed config
            target_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(target_file, 'w', encoding='utf-8') as f:
                await f.write(transformed_content)
            
            self.stats.configs_migrated += 1
            logger.debug(f"Migrated Python config: {config_file} -> {target_file}")
            
        except Exception as e:
            logger.error(f"Error migrating Python config {config_file}: {e}")
            raise
    
    def _transform_python_config(self, content: str, filename: str) -> str:
        """Transform Python configuration content for MCP system"""
        try:
            # Basic transformations
            transformations = {
                # Import updates
                "from app.claude_ai": "from app.mcp_sistema",
                "import claude_ai": "import mcp_sistema",
                "claude_ai.": "mcp_sistema.",
                
                # Class name updates
                "class ClaudeConfig": "class MCPConfig",
                "class ClaudeAIConfig": "class MCPConfig",
                
                # Variable name updates
                "CLAUDE_AI_": "MCP_",
                "claude_ai_": "mcp_",
                "ClaudeAI": "MCP",
                
                # Path updates
                "claude_ai_novo": "mcp_sistema",
                "claude-ai": "mcp-sistema",
                
                # Configuration keys
                '"claude_ai"': '"mcp_sistema"',
                "'claude_ai'": "'mcp_sistema'"
            }
            
            transformed = content
            for old, new in transformations.items():
                transformed = transformed.replace(old, new)
            
            # Add MCP-specific configurations
            mcp_additions = f"""
# MCP System Configuration Additions (migrated from {filename})
MCP_TOOL_TIMEOUT = 30000  # 30 seconds
MCP_MAX_CONCURRENT_TOOLS = 10
MCP_RESOURCE_CACHE_TTL = 300  # 5 minutes
MCP_MAX_RESOURCE_SIZE = 10_000_000  # 10MB

# Migration metadata
MIGRATION_INFO = {{
    "source_file": "{filename}",
    "migration_date": "{datetime.datetime.utcnow().isoformat()}",
    "migrated_from": "claude_ai_novo"
}}
"""
            
            # Append MCP additions if not already present
            if "MCP_TOOL_TIMEOUT" not in transformed:
                transformed += mcp_additions
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming Python config: {e}")
            return content  # Return original on error
    
    async def migrate_json_configs(self) -> bool:
        """Migrate JSON configuration files"""
        try:
            logger.info("Starting JSON configuration migration...")
            
            json_configs = list(self.source_path.rglob("*config*.json"))
            json_configs.extend(list(self.source_path.rglob("*settings*.json")))
            
            for config_file in json_configs:
                try:
                    await self._migrate_json_config(config_file)
                except Exception as e:
                    logger.error(f"Error migrating JSON config {config_file}: {e}")
                    self.stats.errors.append(f"JSON config error: {config_file} - {e}")
            
            logger.info("JSON configuration migration complete")
            return True
            
        except Exception as e:
            logger.error(f"JSON config migration failed: {e}")
            self.stats.errors.append(f"JSON config migration error: {e}")
            return False
    
    async def _migrate_json_config(self, config_file: Path):
        """Migrate individual JSON configuration file"""
        try:
            # Read source file
            async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse JSON
            config_data = json.loads(content)
            
            # Create backup
            backup_path = self.backup_dir / config_file.name
            shutil.copy2(config_file, backup_path)
            self.stats.backup_files_created += 1
            
            # Transform configuration data
            transformed_data = self._transform_json_config(config_data, config_file.name)
            
            # Determine target file
            target_file = self._get_target_config_path(config_file)
            
            # Write transformed config
            target_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(target_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(transformed_data, indent=2))
            
            self.stats.configs_migrated += 1
            logger.debug(f"Migrated JSON config: {config_file} -> {target_file}")
            
        except Exception as e:
            logger.error(f"Error migrating JSON config {config_file}: {e}")
            raise
    
    def _transform_json_config(self, config_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Transform JSON configuration data for MCP system"""
        try:
            transformed = config_data.copy()
            
            # Transform keys recursively
            def transform_keys(obj):
                if isinstance(obj, dict):
                    new_obj = {}
                    for key, value in obj.items():
                        # Transform key names
                        new_key = key
                        if "claude_ai" in key.lower():
                            new_key = key.replace("claude_ai", "mcp").replace("claude-ai", "mcp")
                        elif "claude" in key.lower() and "ai" in key.lower():
                            new_key = key.replace("claude", "mcp").replace("ai", "")
                        
                        new_obj[new_key] = transform_keys(value)
                    return new_obj
                elif isinstance(obj, list):
                    return [transform_keys(item) for item in obj]
                elif isinstance(obj, str):
                    # Transform string values
                    if "claude_ai" in obj.lower():
                        return obj.replace("claude_ai", "mcp_sistema").replace("claude-ai", "mcp-sistema")
                    return obj
                else:
                    return obj
            
            transformed = transform_keys(transformed)
            
            # Add MCP-specific configurations
            transformed["mcp_system"] = {
                "name": "freight-mcp",
                "description": "MCP server for freight management system",
                "version": "1.0.0",
                "transport": "stdio",
                "features": {
                    "tools": True,
                    "resources": True,
                    "prompts": False,
                    "sampling": False
                }
            }
            
            # Add migration metadata
            transformed["migration_info"] = {
                "source_file": filename,
                "migration_date": datetime.datetime.utcnow().isoformat(),
                "migrated_from": "claude_ai_novo"
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming JSON config: {e}")
            return config_data  # Return original on error
    
    async def migrate_environment_variables(self) -> bool:
        """Migrate environment variables and .env files"""
        try:
            logger.info("Starting environment variables migration...")
            
            # Find .env files
            env_files = list(self.source_path.rglob(".env*"))
            env_files.extend(list(self.source_path.rglob("*.env")))
            
            for env_file in env_files:
                try:
                    await self._migrate_env_file(env_file)
                except Exception as e:
                    logger.error(f"Error migrating env file {env_file}: {e}")
                    self.stats.errors.append(f"Env file error: {env_file} - {e}")
            
            # Create MCP-specific .env file
            await self._create_mcp_env_file()
            
            logger.info("Environment variables migration complete")
            return True
            
        except Exception as e:
            logger.error(f"Environment variables migration failed: {e}")
            self.stats.errors.append(f"Environment variables migration error: {e}")
            return False
    
    async def _migrate_env_file(self, env_file: Path):
        """Migrate individual .env file"""
        try:
            # Read source file
            async with aiofiles.open(env_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Create backup
            backup_path = self.backup_dir / env_file.name
            shutil.copy2(env_file, backup_path)
            self.stats.backup_files_created += 1
            
            # Transform environment variables
            transformed_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse variable
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Transform key if mapping exists
                        if key in self.env_mappings:
                            new_key = self.env_mappings[key]
                            transformed_lines.append(f"{new_key}={value}")
                            self.stats.env_vars_migrated += 1
                        else:
                            transformed_lines.append(line)
                    else:
                        transformed_lines.append(line)
                else:
                    transformed_lines.append(line)
            
            # Write transformed .env file
            target_file = self.target_path / env_file.name
            async with aiofiles.open(target_file, 'w', encoding='utf-8') as f:
                await f.write('\n'.join(transformed_lines))
            
            logger.debug(f"Migrated env file: {env_file} -> {target_file}")
            
        except Exception as e:
            logger.error(f"Error migrating env file {env_file}: {e}")
            raise
    
    async def _create_mcp_env_file(self):
        """Create MCP-specific environment file"""
        try:
            mcp_env_content = f"""# MCP System Environment Configuration
# Generated during migration from claude_ai_novo
# Migration Date: {datetime.datetime.utcnow().isoformat()}

# MCP Server Configuration
MCP_SERVER_NAME=freight-mcp
MCP_SERVER_DESCRIPTION=MCP server for freight management system
MCP_SERVER_VERSION=1.0.0
MCP_TRANSPORT=stdio

# Tool Configuration
MCP_TOOL_TIMEOUT=30000
MCP_MAX_CONCURRENT_TOOLS=10

# Resource Configuration
MCP_RESOURCE_CACHE_TTL=300
MCP_MAX_RESOURCE_SIZE=10000000

# Database Configuration
# MCP_DATABASE_URL=your_database_url_here

# Cache Configuration
# MCP_REDIS_URL=redis://localhost:6379/0

# Security Configuration
# MCP_SECRET_KEY=your_secret_key_here

# Logging Configuration
MCP_LOG_LEVEL=INFO

# Migration Configuration
MIGRATION_SOURCE=claude_ai_novo
MIGRATION_DATE={datetime.datetime.utcnow().isoformat()}
"""
            
            target_file = self.target_path / ".env.mcp"
            async with aiofiles.open(target_file, 'w', encoding='utf-8') as f:
                await f.write(mcp_env_content)
            
            logger.info(f"Created MCP environment file: {target_file}")
            
        except Exception as e:
            logger.error(f"Error creating MCP env file: {e}")
            raise
    
    def _get_target_config_path(self, source_file: Path) -> Path:
        """Determine target path for configuration file"""
        filename = source_file.name
        
        # Use mapping if available
        if filename in self.config_mappings:
            return self.target_path / self.config_mappings[filename]
        
        # Default mapping based on content/location
        if "security" in filename.lower():
            return self.target_path / "core" / filename
        elif "development" in filename.lower() or "dev" in filename.lower():
            return self.target_path / "config" / filename
        elif "global" in filename.lower() or "system" in filename.lower():
            return self.target_path / "config" / filename
        else:
            return self.target_path / "config" / filename
    
    async def create_migration_summary(self) -> Dict[str, Any]:
        """Create configuration migration summary"""
        summary = {
            "migration_timestamp": datetime.datetime.utcnow().isoformat(),
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "backup_path": str(self.backup_dir),
            "statistics": asdict(self.stats),
            "success": len(self.stats.errors) == 0,
            "config_mappings_used": self.config_mappings,
            "env_mappings_used": self.env_mappings,
            "recommendations": []
        }
        
        # Add recommendations
        if self.stats.configs_migrated > 0:
            summary["recommendations"].append(
                "Review migrated configurations and update any hardcoded paths or references"
            )
        
        if self.stats.env_vars_migrated > 0:
            summary["recommendations"].append(
                "Update deployment scripts to use new environment variable names"
            )
        
        if self.stats.security_settings_migrated > 0:
            summary["recommendations"].append(
                "Verify security configurations are properly applied in MCP system"
            )
        
        if self.stats.backup_files_created > 0:
            summary["recommendations"].append(
                f"Backup files created in {self.backup_dir} - keep for rollback if needed"
            )
        
        return summary
    
    async def run_migration(self) -> Dict[str, Any]:
        """Run complete configuration migration"""
        logger.info("=== Starting Configuration Migration ===")
        
        try:
            # Analyze source configurations
            analysis = await self.analyze_source_configs()
            logger.info(f"Configuration analysis: {analysis}")
            
            # Run migrations
            migration_tasks = [
                self.migrate_python_configs(),
                self.migrate_json_configs(),
                self.migrate_environment_variables()
            ]
            
            results = await asyncio.gather(*migration_tasks, return_exceptions=True)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Config migration task {i} failed: {result}")
                    self.stats.errors.append(f"Task {i} failed: {result}")
            
            # Create summary
            summary = await self.create_migration_summary()
            
            # Save summary
            summary_path = Path("migration_summary_config.json")
            async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, default=str))
            
            logger.info(f"Configuration migration complete! Summary: {summary_path}")
            logger.info(f"Statistics: {self.stats}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Configuration migration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "statistics": asdict(self.stats)
            }

async def main():
    """Main configuration migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate configurations from claude_ai_novo to MCP system")
    parser.add_argument("--source", help="Source configuration path")
    parser.add_argument("--target", help="Target configuration path")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, no migration")
    
    args = parser.parse_args()
    
    migrator = ConfigurationMigrator(
        source_path=args.source,
        target_path=args.target
    )
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        analysis = await migrator.analyze_source_configs()
        print(json.dumps(analysis, indent=2, default=str))
    else:
        result = await migrator.run_migration()
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())