#!/usr/bin/env python3
"""
Migration Rollback Procedures
Provides rollback capabilities for migration from claude_ai_novo to MCP system

Features:
- Complete system rollback
- Selective component rollback
- Backup restoration
- Data integrity verification
- Recovery procedures
"""

import os
import sys
import json
import logging
import datetime
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiofiles

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.mcp_sistema.models.database import DatabaseManager
from app.mcp_sistema.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_rollback.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RollbackPlan:
    """Rollback execution plan"""
    restore_database: bool = True
    restore_configurations: bool = True
    restore_source_data: bool = True
    cleanup_migrated_data: bool = True
    verify_restoration: bool = True
    create_rollback_report: bool = True

@dataclass
class RollbackResults:
    """Results from rollback operations"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    warnings: int = 0
    errors: List[str] = None
    warnings_list: List[str] = None
    operation_details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings_list is None:
            self.warnings_list = []
        if self.operation_details is None:
            self.operation_details = {}
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100

class MigrationRollbackManager:
    """Main class for migration rollback operations"""
    
    def __init__(self, backup_path: str = None, target_db_url: str = None, plan: RollbackPlan = None):
        """
        Initialize rollback manager
        
        Args:
            backup_path: Path to backup files
            target_db_url: Target MCP database URL
            plan: Rollback execution plan
        """
        self.backup_path = Path(backup_path) if backup_path else self._find_latest_backup()
        self.target_db_url = target_db_url
        self.plan = plan or RollbackPlan()
        self.config = load_config()
        self.db_manager = None
        self.results = RollbackResults()
        
        # Create rollback workspace
        self.workspace = Path("rollback_workspace") / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized rollback manager: backup={self.backup_path}")
        logger.info(f"Rollback workspace: {self.workspace}")
    
    def _find_latest_backup(self) -> Optional[Path]:
        """Find the latest backup directory"""
        try:
            # Look for backup directories
            backup_patterns = [
                "migration_workspace/*/backups/pre_migration",
                "migration/backups",
                "backups",
                "*/backups"
            ]
            
            latest_backup = None
            latest_time = None
            
            for pattern in backup_patterns:
                backup_dirs = list(Path(".").glob(pattern))
                for backup_dir in backup_dirs:
                    if backup_dir.is_dir():
                        # Check modification time
                        mod_time = backup_dir.stat().st_mtime
                        if latest_time is None or mod_time > latest_time:
                            latest_time = mod_time
                            latest_backup = backup_dir
            
            if latest_backup:
                logger.info(f"Found latest backup: {latest_backup}")
                return latest_backup
            else:
                logger.warning("No backup directory found")
                return None
                
        except Exception as e:
            logger.error(f"Error finding latest backup: {e}")
            return None
    
    async def initialize(self):
        """Initialize database connections"""
        try:
            if self.target_db_url:
                self.db_manager = DatabaseManager(self.target_db_url)
                await self.db_manager.initialize()
            
            logger.info("Rollback system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize rollback system: {e}")
            self.results.errors.append(f"Initialization error: {e}")
            return False
    
    async def analyze_backup(self) -> Dict[str, Any]:
        """Analyze available backup files"""
        analysis = {
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "backup_exists": False,
            "backup_files": [],
            "backup_manifest": None,
            "database_backup": None,
            "config_backups": [],
            "source_backup": None,
            "total_size_mb": 0
        }
        
        try:
            if not self.backup_path or not self.backup_path.exists():
                logger.warning("Backup path does not exist")
                return analysis
            
            analysis["backup_exists"] = True
            
            # Scan backup files
            for backup_file in self.backup_path.rglob("*"):
                if backup_file.is_file():
                    size_mb = backup_file.stat().st_size / (1024 * 1024)
                    analysis["total_size_mb"] += size_mb
                    
                    file_info = {
                        "path": str(backup_file),
                        "relative_path": str(backup_file.relative_to(self.backup_path)),
                        "size_mb": size_mb,
                        "last_modified": datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
                    }
                    
                    analysis["backup_files"].append(file_info)
                    
                    # Categorize files
                    if "manifest" in backup_file.name.lower():
                        analysis["backup_manifest"] = file_info
                    elif "database" in backup_file.name.lower() or backup_file.suffix == ".db":
                        analysis["database_backup"] = file_info
                    elif "config" in backup_file.name.lower():
                        analysis["config_backups"].append(file_info)
                    elif "backup.tar.gz" in backup_file.name or "claude_ai_novo" in backup_file.name:
                        analysis["source_backup"] = file_info
            
            # Read backup manifest if available
            if analysis["backup_manifest"]:
                try:
                    manifest_path = Path(analysis["backup_manifest"]["path"])
                    async with aiofiles.open(manifest_path, 'r') as f:
                        manifest_content = await f.read()
                    analysis["backup_manifest"]["content"] = json.loads(manifest_content)
                except Exception as e:
                    logger.warning(f"Could not read backup manifest: {e}")
            
            logger.info(f"Backup analysis complete: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing backup: {e}")
            self.results.errors.append(f"Backup analysis error: {e}")
            return analysis
    
    async def restore_database(self) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            if not self.plan.restore_database:
                logger.info("Database restoration disabled in plan")
                return {"status": "skipped", "reason": "disabled_in_plan"}
            
            logger.info("Starting database restoration...")
            
            # Find database backup
            backup_analysis = await self.analyze_backup()
            db_backup_info = backup_analysis.get("database_backup")
            
            if not db_backup_info:
                logger.error("No database backup found")
                return {"status": "failed", "error": "No database backup found"}
            
            db_backup_path = Path(db_backup_info["path"])
            
            # Determine target database path
            if self.target_db_url and "sqlite" in self.target_db_url:
                target_db_path = self.target_db_url.replace("sqlite:///", "")
            else:
                logger.error("Cannot restore non-SQLite database")
                return {"status": "failed", "error": "Cannot restore non-SQLite database"}
            
            # Create backup of current database
            current_db_path = Path(target_db_path)
            if current_db_path.exists():
                current_backup = self.workspace / f"current_db_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(current_db_path, current_backup)
                logger.info(f"Current database backed up to: {current_backup}")
            
            # Restore database
            shutil.copy2(db_backup_path, current_db_path)
            logger.info(f"Database restored from: {db_backup_path}")
            
            # Verify restoration
            try:
                conn = sqlite3.connect(str(current_db_path))
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                verification_result = {
                    "tables_found": len(tables),
                    "tables": [table[0] for table in tables]
                }
                
                logger.info(f"Database verification: {verification_result}")
                
            except Exception as e:
                logger.error(f"Database verification failed: {e}")
                verification_result = {"error": str(e)}
            
            return {
                "status": "success",
                "backup_source": str(db_backup_path),
                "target_path": target_db_path,
                "verification": verification_result
            }
            
        except Exception as e:
            logger.error(f"Database restoration failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def restore_configurations(self) -> Dict[str, Any]:
        """Restore configuration files from backup"""
        try:
            if not self.plan.restore_configurations:
                logger.info("Configuration restoration disabled in plan")
                return {"status": "skipped", "reason": "disabled_in_plan"}
            
            logger.info("Starting configuration restoration...")
            
            backup_analysis = await self.analyze_backup()
            config_backups = backup_analysis.get("config_backups", [])
            
            restored_configs = []
            restoration_errors = []
            
            # Look for configuration backup directory
            config_backup_dir = None
            if self.backup_path:
                potential_config_dirs = [
                    self.backup_path / "config",
                    self.backup_path / "configurations",
                    self.backup_path.parent / "config"
                ]
                
                for config_dir in potential_config_dirs:
                    if config_dir.exists():
                        config_backup_dir = config_dir
                        break
            
            if config_backup_dir:
                # Restore configuration files
                target_config_dir = Path("app/mcp_sistema/config")
                target_config_dir.mkdir(parents=True, exist_ok=True)
                
                for config_file in config_backup_dir.rglob("*"):
                    if config_file.is_file():
                        try:
                            relative_path = config_file.relative_to(config_backup_dir)
                            target_file = target_config_dir / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Backup current config if exists
                            if target_file.exists():
                                current_backup = self.workspace / f"config_backup_{target_file.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                shutil.copy2(target_file, current_backup)
                            
                            # Restore config
                            shutil.copy2(config_file, target_file)
                            restored_configs.append(str(relative_path))
                            
                        except Exception as e:
                            restoration_errors.append(f"{config_file}: {e}")
                            logger.error(f"Error restoring config {config_file}: {e}")
            
            # Restore environment files
            env_files = [".env", ".env.mcp", ".env.backup"]
            for env_file in env_files:
                backup_env = self.backup_path / env_file if self.backup_path else None
                if backup_env and backup_env.exists():
                    try:
                        target_env = Path(env_file)
                        if target_env.exists():
                            current_backup = self.workspace / f"env_backup_{env_file}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.copy2(target_env, current_backup)
                        
                        shutil.copy2(backup_env, target_env)
                        restored_configs.append(env_file)
                        
                    except Exception as e:
                        restoration_errors.append(f"{env_file}: {e}")
                        logger.error(f"Error restoring env file {env_file}: {e}")
            
            if restored_configs:
                status = "success" if not restoration_errors else "partial"
            else:
                status = "failed" if restoration_errors else "no_configs_found"
            
            return {
                "status": status,
                "restored_configs": restored_configs,
                "restoration_errors": restoration_errors,
                "total_restored": len(restored_configs)
            }
            
        except Exception as e:
            logger.error(f"Configuration restoration failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def restore_source_data(self) -> Dict[str, Any]:
        """Restore source claude_ai_novo data from backup"""
        try:
            if not self.plan.restore_source_data:
                logger.info("Source data restoration disabled in plan")
                return {"status": "skipped", "reason": "disabled_in_plan"}
            
            logger.info("Starting source data restoration...")
            
            backup_analysis = await self.analyze_backup()
            source_backup_info = backup_analysis.get("source_backup")
            
            if not source_backup_info:
                logger.warning("No source data backup found")
                return {"status": "no_backup", "reason": "No source data backup found"}
            
            source_backup_path = Path(source_backup_info["path"])
            
            # Determine restoration target
            target_path = Path("app/claude_ai_novo_restored")
            
            # Create backup of current source if exists
            current_source = Path("app/claude_ai_novo")
            if current_source.exists():
                current_backup = self.workspace / f"current_source_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(current_source, current_backup)
                logger.info(f"Current source backed up to: {current_backup}")
            
            # Extract source backup
            if source_backup_path.suffix == ".gz":
                # Extract tar.gz backup
                subprocess.run([
                    "tar", "-xzf", str(source_backup_path),
                    "-C", str(target_path.parent)
                ], check=True)
                logger.info(f"Source data extracted to: {target_path}")
                
                # Verify extraction
                if target_path.exists():
                    extracted_files = list(target_path.rglob("*"))
                    verification_result = {
                        "extracted_files": len(extracted_files),
                        "total_size_mb": sum(f.stat().st_size for f in extracted_files if f.is_file()) / (1024 * 1024)
                    }
                else:
                    verification_result = {"error": "Extraction failed - target path not found"}
                
            else:
                # Copy directory backup
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(source_backup_path, target_path)
                
                verification_result = {
                    "copied_files": len(list(target_path.rglob("*"))),
                    "total_size_mb": sum(f.stat().st_size for f in target_path.rglob("*") if f.is_file()) / (1024 * 1024)
                }
            
            return {
                "status": "success",
                "backup_source": str(source_backup_path),
                "target_path": str(target_path),
                "verification": verification_result
            }
            
        except Exception as e:
            logger.error(f"Source data restoration failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def cleanup_migrated_data(self) -> Dict[str, Any]:
        """Clean up migrated data from MCP system"""
        try:
            if not self.plan.cleanup_migrated_data:
                logger.info("Migrated data cleanup disabled in plan")
                return {"status": "skipped", "reason": "disabled_in_plan"}
            
            logger.info("Starting migrated data cleanup...")
            
            cleanup_results = {
                "sessions_cleaned": 0,
                "resources_cleaned": 0,
                "logs_cleaned": 0,
                "errors": []
            }
            
            if self.db_manager:
                async with self.db_manager.get_session() as session:
                    try:
                        # Clean up migrated sessions
                        result = await session.execute(
                            "DELETE FROM mcp_sessions WHERE metadata LIKE '%migrated%'"
                        )
                        cleanup_results["sessions_cleaned"] = result.rowcount
                        
                        # Clean up migrated resources
                        result = await session.execute(
                            "DELETE FROM mcp_resources WHERE metadata LIKE '%migrated%'"
                        )
                        cleanup_results["resources_cleaned"] = result.rowcount
                        
                        # Clean up migration logs
                        result = await session.execute(
                            "DELETE FROM mcp_logs WHERE message LIKE '%migration%'"
                        )
                        cleanup_results["logs_cleaned"] = result.rowcount
                        
                        await session.commit()
                        logger.info(f"Cleanup completed: {cleanup_results}")
                        
                    except Exception as e:
                        cleanup_results["errors"].append(str(e))
                        logger.error(f"Database cleanup error: {e}")
                        await session.rollback()
            
            # Clean up migration files
            migration_files = [
                "migration_summary_*.json",
                "migration_*.log",
                "*migration*.json"
            ]
            
            cleaned_files = []
            for pattern in migration_files:
                for file_path in Path(".").glob(pattern):
                    try:
                        # Move to workspace instead of deleting
                        backup_file = self.workspace / file_path.name
                        shutil.move(str(file_path), str(backup_file))
                        cleaned_files.append(str(file_path))
                    except Exception as e:
                        cleanup_results["errors"].append(f"{file_path}: {e}")
            
            cleanup_results["files_cleaned"] = len(cleaned_files)
            cleanup_results["cleaned_files"] = cleaned_files
            
            if cleanup_results["errors"]:
                status = "partial"
            else:
                status = "success"
            
            return {
                "status": status,
                "cleanup_results": cleanup_results
            }
            
        except Exception as e:
            logger.error(f"Migrated data cleanup failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def verify_rollback(self) -> Dict[str, Any]:
        """Verify rollback operation success"""
        try:
            if not self.plan.verify_restoration:
                logger.info("Rollback verification disabled in plan")
                return {"status": "skipped", "reason": "disabled_in_plan"}
            
            logger.info("Starting rollback verification...")
            
            verification_results = {
                "database_verification": {},
                "config_verification": {},
                "source_verification": {},
                "overall_score": 0
            }
            
            score = 0
            max_score = 100
            
            # Verify database restoration
            if self.target_db_url and "sqlite" in self.target_db_url:
                try:
                    db_path = self.target_db_url.replace("sqlite:///", "")
                    if Path(db_path).exists():
                        conn = sqlite3.connect(db_path)
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]
                        conn.close()
                        
                        # Check for MCP tables (should be minimal after rollback)
                        mcp_tables = [t for t in tables if t.startswith("mcp_")]
                        
                        verification_results["database_verification"] = {
                            "database_exists": True,
                            "total_tables": len(tables),
                            "mcp_tables": len(mcp_tables),
                            "tables": tables
                        }
                        
                        score += 30  # Database exists and accessible
                        if len(mcp_tables) == 0:
                            score += 20  # MCP tables cleaned up
                        
                    else:
                        verification_results["database_verification"] = {"database_exists": False}
                        
                except Exception as e:
                    verification_results["database_verification"] = {"error": str(e)}
            
            # Verify configuration restoration
            config_files = ["config.py", ".env", "settings.json"]
            restored_configs = 0
            for config_file in config_files:
                config_path = Path(f"app/mcp_sistema/config/{config_file}") if config_file != ".env" else Path(config_file)
                if config_path.exists():
                    restored_configs += 1
            
            verification_results["config_verification"] = {
                "configs_checked": len(config_files),
                "configs_found": restored_configs
            }
            
            if restored_configs > 0:
                score += 25  # Some configs restored
            
            # Verify source data restoration
            source_paths = [
                Path("app/claude_ai_novo"),
                Path("app/claude_ai_novo_restored")
            ]
            
            source_exists = False
            for source_path in source_paths:
                if source_path.exists():
                    source_exists = True
                    files_count = len(list(source_path.rglob("*")))
                    verification_results["source_verification"] = {
                        "source_exists": True,
                        "source_path": str(source_path),
                        "files_count": files_count
                    }
                    break
            
            if not source_exists:
                verification_results["source_verification"] = {"source_exists": False}
            else:
                score += 25  # Source data restored
            
            verification_results["overall_score"] = score
            
            # Determine verification status
            if score >= 80:
                status = "success"
            elif score >= 60:
                status = "partial"
            else:
                status = "failed"
            
            return {
                "status": status,
                "verification_results": verification_results,
                "score": score,
                "max_score": max_score
            }
            
        except Exception as e:
            logger.error(f"Rollback verification failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def create_rollback_report(self) -> Dict[str, Any]:
        """Create comprehensive rollback report"""
        try:
            rollback_report = {
                "rollback_timestamp": datetime.datetime.utcnow().isoformat(),
                "backup_path": str(self.backup_path) if self.backup_path else None,
                "rollback_plan": asdict(self.plan),
                "results_summary": asdict(self.results),
                "operation_details": self.results.operation_details,
                "recommendations": []
            }
            
            # Generate recommendations
            if self.results.success_rate >= 90:
                rollback_report["recommendations"].extend([
                    "Rollback completed successfully",
                    "Verify system functionality",
                    "Update documentation to reflect rollback",
                    "Consider reviewing migration failures before retry"
                ])
            elif self.results.success_rate >= 70:
                rollback_report["recommendations"].extend([
                    "Rollback partially successful",
                    "Review failed operations and manual intervention may be required",
                    "Verify critical system components",
                    "Test system functionality before use"
                ])
            else:
                rollback_report["recommendations"].extend([
                    "Rollback encountered significant issues",
                    "Manual intervention required",
                    "Contact system administrator",
                    "Do not use system until issues are resolved"
                ])
            
            if self.results.errors:
                rollback_report["recommendations"].append(
                    f"Address {len(self.results.errors)} errors identified during rollback"
                )
            
            # Save report
            report_path = self.workspace / "rollback_report.json"
            async with aiofiles.open(report_path, 'w') as f:
                await f.write(json.dumps(rollback_report, indent=2, default=str))
            
            # Also save to root level
            root_report_path = Path("migration_rollback_report.json")
            async with aiofiles.open(root_report_path, 'w') as f:
                await f.write(json.dumps(rollback_report, indent=2, default=str))
            
            logger.info(f"Rollback report saved: {report_path}")
            logger.info(f"Report also available at: {root_report_path}")
            
            return rollback_report
            
        except Exception as e:
            logger.error(f"Error creating rollback report: {e}")
            return {"error": str(e)}
    
    async def run_complete_rollback(self) -> Dict[str, Any]:
        """Run complete rollback operation"""
        logger.info("="*80)
        logger.info("Starting Complete Migration Rollback")
        logger.info("="*80)
        
        try:
            # Initialize rollback system
            if not await self.initialize():
                return {"success": False, "error": "Failed to initialize rollback system"}
            
            # Analyze backup
            backup_analysis = await self.analyze_backup()
            if not backup_analysis.get("backup_exists"):
                return {"success": False, "error": "No backup found for rollback"}
            
            # Define rollback operations
            rollback_operations = [
                ("Database Restoration", self.restore_database),
                ("Configuration Restoration", self.restore_configurations),
                ("Source Data Restoration", self.restore_source_data),
                ("Migrated Data Cleanup", self.cleanup_migrated_data),
                ("Rollback Verification", self.verify_rollback)
            ]
            
            # Execute rollback operations
            for operation_name, operation_func in rollback_operations:
                logger.info(f"Executing: {operation_name}")
                
                try:
                    result = await operation_func()
                    self.results.operation_details[operation_name] = result
                    self.results.total_operations += 1
                    
                    if result.get("status") in ["success", "skipped"]:
                        self.results.successful_operations += 1
                        logger.info(f"✅ {operation_name}: {result.get('status')}")
                    elif result.get("status") == "partial":
                        self.results.successful_operations += 1
                        self.results.warnings += 1
                        self.results.warnings_list.append(f"{operation_name}: Partial success")
                        logger.warning(f"⚠️ {operation_name}: Partial success")
                    else:
                        self.results.failed_operations += 1
                        error_msg = result.get("error", "Unknown error")
                        self.results.errors.append(f"{operation_name}: {error_msg}")
                        logger.error(f"❌ {operation_name}: {error_msg}")
                        
                except Exception as e:
                    self.results.total_operations += 1
                    self.results.failed_operations += 1
                    self.results.errors.append(f"{operation_name}: {e}")
                    logger.error(f"❌ {operation_name} failed with exception: {e}")
            
            # Create rollback report
            if self.plan.create_rollback_report:
                rollback_report = await self.create_rollback_report()
            else:
                rollback_report = {"report": "disabled"}
            
            # Final status
            overall_success = self.results.success_rate >= 80
            
            logger.info("="*80)
            if overall_success:
                logger.info("✅ ROLLBACK COMPLETED SUCCESSFULLY")
            else:
                logger.error("❌ ROLLBACK COMPLETED WITH ISSUES")
            logger.info(f"Success rate: {self.results.success_rate:.1f}%")
            logger.info(f"Operations: {self.results.successful_operations}/{self.results.total_operations}")
            logger.info(f"Errors: {len(self.results.errors)}")
            logger.info("="*80)
            
            return {
                "success": overall_success,
                "results": asdict(self.results),
                "rollback_report": rollback_report
            }
            
        except Exception as e:
            logger.error(f"Complete rollback failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": asdict(self.results)
            }
        
        finally:
            # Cleanup
            if self.db_manager:
                await self.db_manager.close()

async def main():
    """Main rollback entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Rollback migration from MCP system to claude_ai_novo")
    parser.add_argument("--backup-path", help="Path to backup files")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--no-database", action="store_true", help="Skip database restoration")
    parser.add_argument("--no-config", action="store_true", help="Skip configuration restoration")
    parser.add_argument("--no-source", action="store_true", help="Skip source data restoration")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip migrated data cleanup")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze backup, don't rollback")
    
    args = parser.parse_args()
    
    # Create rollback plan
    plan = RollbackPlan(
        restore_database=not args.no_database,
        restore_configurations=not args.no_config,
        restore_source_data=not args.no_source,
        cleanup_migrated_data=not args.no_cleanup,
        verify_restoration=not args.no_verify
    )
    
    # Create rollback manager
    rollback_manager = MigrationRollbackManager(
        backup_path=args.backup_path,
        target_db_url=args.target_db,
        plan=plan
    )
    
    if args.analyze_only:
        # Just analyze backup
        await rollback_manager.initialize()
        analysis = await rollback_manager.analyze_backup()
        print(json.dumps(analysis, indent=2, default=str))
    else:
        # Run complete rollback
        result = await rollback_manager.run_complete_rollback()
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())