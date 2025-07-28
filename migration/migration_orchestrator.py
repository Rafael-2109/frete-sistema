#!/usr/bin/env python3
"""
Migration Orchestrator
Coordinates the complete migration process from claude_ai_novo to MCP system

Features:
- Complete migration workflow orchestration
- Parallel migration execution
- Error handling and recovery
- Progress monitoring
- Rollback capabilities
- Comprehensive reporting
"""

import os
import sys
import json
import logging
import datetime
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import aiofiles

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import migration modules
from migration.claude_ai_migration import ClaudeAIDataMigrator
from migration.config_migrator import ConfigurationMigrator
from migration.knowledge_migrator import KnowledgeBaseMigrator
from migration.session_migrator import SessionMigrator
from migration.validation_scripts import MigrationValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MigrationPlan:
    """Migration execution plan"""
    phase_1_data: bool = True
    phase_2_config: bool = True
    phase_3_knowledge: bool = True
    phase_4_sessions: bool = True
    phase_5_validation: bool = True
    parallel_execution: bool = True
    create_backups: bool = True
    run_validations: bool = True
    rollback_on_failure: bool = False

@dataclass
class MigrationProgress:
    """Track migration progress"""
    total_phases: int = 5
    completed_phases: int = 0
    current_phase: str = ""
    start_time: datetime.datetime = None
    end_time: datetime.datetime = None
    phase_results: Dict[str, Any] = None
    overall_success: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.datetime.utcnow()
        if self.phase_results is None:
            self.phase_results = {}
        if self.errors is None:
            self.errors = []
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        return (self.completed_phases / self.total_phases) * 100
    
    @property
    def elapsed_time(self) -> str:
        """Calculate elapsed time"""
        end = self.end_time or datetime.datetime.utcnow()
        delta = end - self.start_time
        return str(delta)

class MigrationOrchestrator:
    """Main orchestrator for the complete migration process"""
    
    def __init__(self, source_path: str = None, target_db_url: str = None, plan: MigrationPlan = None):
        """
        Initialize migration orchestrator
        
        Args:
            source_path: Source claude_ai_novo path
            target_db_url: Target MCP database URL
            plan: Migration execution plan
        """
        self.source_path = source_path or "app/claude_ai_novo"
        self.target_db_url = target_db_url
        self.plan = plan or MigrationPlan()
        self.progress = MigrationProgress()
        
        # Create migration workspace
        self.workspace = Path("migration_workspace") / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Migration components
        self.migrators = {}
        self.validator = None
        
        logger.info(f"Initialized migration orchestrator: {self.source_path} -> MCP System")
        logger.info(f"Migration workspace: {self.workspace}")
    
    async def initialize_migrators(self):
        """Initialize all migration components"""
        try:
            logger.info("Initializing migration components...")
            
            # Initialize migrators
            self.migrators = {
                "data": ClaudeAIDataMigrator(self.source_path, self.target_db_url),
                "config": ConfigurationMigrator(self.source_path, "app/mcp_sistema"),
                "knowledge": KnowledgeBaseMigrator(self.source_path, self.target_db_url),
                "sessions": SessionMigrator(self.source_path, self.target_db_url)
            }
            
            # Initialize validator
            self.validator = MigrationValidator(self.source_path, self.target_db_url)
            
            logger.info("Migration components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize migration components: {e}")
            self.progress.errors.append(f"Initialization error: {e}")
            return False
    
    async def create_pre_migration_backup(self) -> bool:
        """Create backup before migration"""
        try:
            if not self.plan.create_backups:
                logger.info("Backup creation disabled in plan")
                return True
            
            logger.info("Creating pre-migration backup...")
            
            backup_dir = self.workspace / "backups" / "pre_migration"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup source data
            source_backup = backup_dir / "claude_ai_novo_backup.tar.gz"
            if Path(self.source_path).exists():
                subprocess.run([
                    "tar", "-czf", str(source_backup), 
                    "-C", str(Path(self.source_path).parent),
                    Path(self.source_path).name
                ], check=True)
                logger.info(f"Source backup created: {source_backup}")
            
            # Backup existing MCP database if it exists
            if self.target_db_url and "sqlite" in self.target_db_url:
                db_path = self.target_db_url.replace("sqlite:///", "")
                if Path(db_path).exists():
                    db_backup = backup_dir / "mcp_database_backup.db"
                    subprocess.run(["cp", db_path, str(db_backup)], check=True)
                    logger.info(f"Database backup created: {db_backup}")
            
            # Create backup manifest
            backup_manifest = {
                "backup_timestamp": datetime.datetime.utcnow().isoformat(),
                "source_path": self.source_path,
                "target_db_url": self.target_db_url,
                "backup_files": [
                    str(f.relative_to(backup_dir)) for f in backup_dir.glob("*")
                ]
            }
            
            async with aiofiles.open(backup_dir / "backup_manifest.json", 'w') as f:
                await f.write(json.dumps(backup_manifest, indent=2))
            
            logger.info("Pre-migration backup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Pre-migration backup failed: {e}")
            self.progress.errors.append(f"Backup error: {e}")
            return False
    
    async def run_migration_phase(self, phase_name: str, migrator_func) -> Dict[str, Any]:
        """Run individual migration phase with error handling"""
        try:
            logger.info(f"=== Starting Phase: {phase_name} ===")
            self.progress.current_phase = phase_name
            
            start_time = datetime.datetime.utcnow()
            result = await migrator_func()
            end_time = datetime.datetime.utcnow()
            
            # Add timing information
            if isinstance(result, dict):
                result["execution_time_seconds"] = (end_time - start_time).total_seconds()
                result["phase_name"] = phase_name
            
            success = result.get("success", True) if isinstance(result, dict) else True
            
            if success:
                logger.info(f"Phase {phase_name} completed successfully")
                self.progress.completed_phases += 1
            else:
                logger.error(f"Phase {phase_name} failed: {result.get('error', 'Unknown error')}")
                self.progress.errors.append(f"Phase {phase_name}: {result.get('error', 'Unknown error')}")
            
            self.progress.phase_results[phase_name] = result
            return result
            
        except Exception as e:
            logger.error(f"Phase {phase_name} failed with exception: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "phase_name": phase_name
            }
            self.progress.phase_results[phase_name] = error_result
            self.progress.errors.append(f"Phase {phase_name}: {e}")
            return error_result
    
    async def run_parallel_migration(self) -> Dict[str, Any]:
        """Run migration phases in parallel where possible"""
        try:
            logger.info("Starting parallel migration execution...")
            
            # Phase 1: Data and Configuration (can run in parallel)
            parallel_tasks_1 = []
            if self.plan.phase_1_data:
                parallel_tasks_1.append(
                    self.run_migration_phase("Data Migration", self.migrators["data"].run_migration)
                )
            if self.plan.phase_2_config:
                parallel_tasks_1.append(
                    self.run_migration_phase("Configuration Migration", self.migrators["config"].run_migration)
                )
            
            if parallel_tasks_1:
                phase_1_results = await asyncio.gather(*parallel_tasks_1, return_exceptions=True)
                
                # Check for exceptions
                for i, result in enumerate(phase_1_results):
                    if isinstance(result, Exception):
                        logger.error(f"Parallel task {i} failed: {result}")
                        self.progress.errors.append(f"Parallel task {i}: {result}")
            
            # Phase 2: Knowledge and Sessions (can run in parallel, but depend on data migration)
            parallel_tasks_2 = []
            if self.plan.phase_3_knowledge:
                parallel_tasks_2.append(
                    self.run_migration_phase("Knowledge Migration", self.migrators["knowledge"].run_migration)
                )
            if self.plan.phase_4_sessions:
                parallel_tasks_2.append(
                    self.run_migration_phase("Session Migration", self.migrators["sessions"].run_migration)
                )
            
            if parallel_tasks_2:
                phase_2_results = await asyncio.gather(*parallel_tasks_2, return_exceptions=True)
                
                # Check for exceptions
                for i, result in enumerate(phase_2_results):
                    if isinstance(result, Exception):
                        logger.error(f"Parallel task {i} failed: {result}")
                        self.progress.errors.append(f"Parallel task {i}: {result}")
            
            # Phase 3: Validation (must run after all migrations)
            if self.plan.phase_5_validation:
                await self.run_migration_phase("Validation", self.validator.run_all_validations)
            
            logger.info("Parallel migration execution completed")
            return {"success": True, "mode": "parallel"}
            
        except Exception as e:
            logger.error(f"Parallel migration failed: {e}")
            return {"success": False, "error": str(e), "mode": "parallel"}
    
    async def run_sequential_migration(self) -> Dict[str, Any]:
        """Run migration phases sequentially"""
        try:
            logger.info("Starting sequential migration execution...")
            
            # Execute phases in order
            migration_phases = [
                ("Data Migration", self.plan.phase_1_data, self.migrators["data"].run_migration),
                ("Configuration Migration", self.plan.phase_2_config, self.migrators["config"].run_migration),
                ("Knowledge Migration", self.plan.phase_3_knowledge, self.migrators["knowledge"].run_migration),
                ("Session Migration", self.plan.phase_4_sessions, self.migrators["sessions"].run_migration),
                ("Validation", self.plan.phase_5_validation, self.validator.run_all_validations)
            ]
            
            for phase_name, enabled, phase_func in migration_phases:
                if enabled:
                    result = await self.run_migration_phase(phase_name, phase_func)
                    
                    # Check if we should stop on failure
                    if not result.get("success", True) and self.plan.rollback_on_failure:
                        logger.error(f"Phase {phase_name} failed - stopping migration")
                        break
                else:
                    logger.info(f"Phase {phase_name} disabled in plan - skipping")
            
            logger.info("Sequential migration execution completed")
            return {"success": True, "mode": "sequential"}
            
        except Exception as e:
            logger.error(f"Sequential migration failed: {e}")
            return {"success": False, "error": str(e), "mode": "sequential"}
    
    async def handle_migration_failure(self):
        """Handle migration failure and potential rollback"""
        try:
            logger.error("Migration failure detected - initiating failure handling...")
            
            if self.plan.rollback_on_failure:
                logger.info("Rollback enabled - attempting to restore backup...")
                
                # Find backup files
                backup_dir = self.workspace / "backups" / "pre_migration"
                if backup_dir.exists():
                    # Restore database backup
                    db_backup = backup_dir / "mcp_database_backup.db"
                    if db_backup.exists() and self.target_db_url and "sqlite" in self.target_db_url:
                        db_path = self.target_db_url.replace("sqlite:///", "")
                        subprocess.run(["cp", str(db_backup), db_path], check=True)
                        logger.info("Database backup restored")
                    
                    logger.info("Rollback completed")
                else:
                    logger.error("No backup found for rollback")
            else:
                logger.info("Rollback disabled - manual intervention required")
            
            # Create failure report
            await self.create_failure_report()
            
        except Exception as e:
            logger.error(f"Failure handling failed: {e}")
    
    async def create_failure_report(self):
        """Create detailed failure report"""
        try:
            failure_report = {
                "failure_timestamp": datetime.datetime.utcnow().isoformat(),
                "migration_progress": asdict(self.progress),
                "error_summary": self.progress.errors,
                "phase_results": self.progress.phase_results,
                "recommendations": [
                    "Review error logs for specific failure causes",
                    "Check source data integrity and accessibility",
                    "Verify target system configuration and permissions",
                    "Consider running individual migration phases manually"
                ]
            }
            
            failure_path = self.workspace / "migration_failure_report.json"
            async with aiofiles.open(failure_path, 'w') as f:
                await f.write(json.dumps(failure_report, indent=2, default=str))
            
            logger.info(f"Failure report created: {failure_path}")
            
        except Exception as e:
            logger.error(f"Error creating failure report: {e}")
    
    async def create_final_report(self) -> Dict[str, Any]:
        """Create comprehensive migration report"""
        try:
            self.progress.end_time = datetime.datetime.utcnow()
            
            # Determine overall success
            total_errors = len(self.progress.errors)
            self.progress.overall_success = total_errors == 0 and self.progress.completed_phases >= 3
            
            # Create comprehensive report
            final_report = {
                "migration_summary": {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "source_path": self.source_path,
                    "target_db_url": self.target_db_url,
                    "workspace": str(self.workspace),
                    "overall_success": self.progress.overall_success,
                    "execution_mode": "parallel" if self.plan.parallel_execution else "sequential"
                },
                "execution_details": {
                    "total_phases": self.progress.total_phases,
                    "completed_phases": self.progress.completed_phases,
                    "progress_percentage": self.progress.progress_percentage,
                    "total_time": self.progress.elapsed_time,
                    "total_errors": total_errors
                },
                "phase_results": self.progress.phase_results,
                "errors": self.progress.errors,
                "migration_plan": asdict(self.plan),
                "recommendations": []
            }
            
            # Generate recommendations
            if self.progress.overall_success:
                final_report["recommendations"].extend([
                    "Migration completed successfully",
                    "Run post-migration validation tests",
                    "Update system configurations to use MCP endpoints",
                    "Monitor system performance and functionality"
                ])
            else:
                final_report["recommendations"].extend([
                    "Migration encountered errors - review failure details",
                    "Consider re-running failed phases individually",
                    "Verify source data integrity and target system configuration",
                    "Contact support if issues persist"
                ])
            
            if total_errors > 0:
                final_report["recommendations"].append(
                    f"Address {total_errors} errors before deploying to production"
                )
            
            # Save report
            report_path = self.workspace / "migration_final_report.json"
            async with aiofiles.open(report_path, 'w') as f:
                await f.write(json.dumps(final_report, indent=2, default=str))
            
            # Also save to root level for easy access
            root_report_path = Path("migration_final_report.json")
            async with aiofiles.open(root_report_path, 'w') as f:
                await f.write(json.dumps(final_report, indent=2, default=str))
            
            logger.info(f"Final migration report created: {report_path}")
            logger.info(f"Report also available at: {root_report_path}")
            
            return final_report
            
        except Exception as e:
            logger.error(f"Error creating final report: {e}")
            return {"error": str(e)}
    
    async def run_complete_migration(self) -> Dict[str, Any]:
        """Run the complete migration process"""
        logger.info("="*80)
        logger.info("Starting Complete Migration from claude_ai_novo to MCP System")
        logger.info("="*80)
        
        try:
            # Initialize migration components
            if not await self.initialize_migrators():
                return {"success": False, "error": "Failed to initialize migration components"}
            
            # Create pre-migration backup
            if not await self.create_pre_migration_backup():
                logger.warning("Backup creation failed - continuing with migration")
            
            # Execute migration based on plan
            if self.plan.parallel_execution:
                migration_result = await self.run_parallel_migration()
            else:
                migration_result = await self.run_sequential_migration()
            
            # Handle failures if necessary
            if not migration_result.get("success", True) or len(self.progress.errors) > 0:
                await self.handle_migration_failure()
            
            # Create final report
            final_report = await self.create_final_report()
            
            # Log summary
            logger.info("="*80)
            if self.progress.overall_success:
                logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            else:
                logger.error("❌ MIGRATION COMPLETED WITH ERRORS")
            logger.info(f"Progress: {self.progress.completed_phases}/{self.progress.total_phases} phases completed")
            logger.info(f"Total time: {self.progress.elapsed_time}")
            logger.info(f"Errors: {len(self.progress.errors)}")
            logger.info("="*80)
            
            return final_report
            
        except Exception as e:
            logger.error(f"Complete migration failed: {e}")
            self.progress.errors.append(f"Migration orchestrator error: {e}")
            await self.handle_migration_failure()
            
            return {
                "success": False,
                "error": str(e),
                "progress": asdict(self.progress)
            }

async def main():
    """Main orchestrator entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrate complete migration from claude_ai_novo to MCP system")
    parser.add_argument("--source", help="Source claude_ai_novo path", default="app/claude_ai_novo")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--parallel", action="store_true", help="Use parallel execution", default=True)
    parser.add_argument("--sequential", action="store_true", help="Use sequential execution")
    parser.add_argument("--no-backups", action="store_true", help="Skip backup creation")
    parser.add_argument("--no-validation", action="store_true", help="Skip validation phase")
    parser.add_argument("--rollback-on-failure", action="store_true", help="Rollback on failure")
    parser.add_argument("--skip-data", action="store_true", help="Skip data migration")
    parser.add_argument("--skip-config", action="store_true", help="Skip config migration")
    parser.add_argument("--skip-knowledge", action="store_true", help="Skip knowledge migration")
    parser.add_argument("--skip-sessions", action="store_true", help="Skip session migration")
    
    args = parser.parse_args()
    
    # Create migration plan
    plan = MigrationPlan(
        phase_1_data=not args.skip_data,
        phase_2_config=not args.skip_config,
        phase_3_knowledge=not args.skip_knowledge,
        phase_4_sessions=not args.skip_sessions,
        phase_5_validation=not args.no_validation,
        parallel_execution=not args.sequential,
        create_backups=not args.no_backups,
        rollback_on_failure=args.rollback_on_failure
    )
    
    # Create and run orchestrator
    orchestrator = MigrationOrchestrator(
        source_path=args.source,
        target_db_url=args.target_db,
        plan=plan
    )
    
    result = await orchestrator.run_complete_migration()
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())