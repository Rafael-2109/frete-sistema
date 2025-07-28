#!/usr/bin/env python3
"""
Migration Validation Scripts
Validates data integrity and completeness after migration from claude_ai_novo to MCP system

Features:
- Data integrity validation
- Completeness verification
- Performance testing
- Rollback capability validation
- Migration quality assessment
"""

import os
import sys
import json
import logging
import datetime
import hashlib
import sqlite3
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
from app.mcp_sistema.services.mcp.resources import ResourceManager
from app.mcp_sistema.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResults:
    """Results from validation tests"""
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    total_tests: int = 0
    errors: List[str] = None
    warnings_list: List[str] = None
    test_details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings_list is None:
            self.warnings_list = []
        if self.test_details is None:
            self.test_details = {}
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

class MigrationValidator:
    """Main class for migration validation"""
    
    def __init__(self, source_path: str = None, target_db_url: str = None):
        """
        Initialize migration validator
        
        Args:
            source_path: Path to original claude_ai_novo data
            target_db_url: Target MCP database URL
        """
        self.source_path = Path(source_path) if source_path else Path("app/claude_ai_novo")
        self.target_db_url = target_db_url
        self.config = load_config()
        self.db_manager = None
        self.session_manager = None
        self.resource_manager = None
        self.results = ValidationResults()
        
        # Migration summary files to validate against
        self.migration_summaries = [
            "migration_summary_claude_ai.json",
            "migration_summary_config.json", 
            "migration_summary_knowledge.json",
            "migration_summary_sessions.json"
        ]
        
        logger.info(f"Initialized migration validator: {self.source_path} -> MCP System")
    
    async def initialize(self):
        """Initialize database connections and managers"""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.target_db_url or self.config.database.url)
            await self.db_manager.initialize()
            
            # Initialize managers
            self.session_manager = SessionManager(self.db_manager)
            self.resource_manager = ResourceManager(self.db_manager)
            
            logger.info("Validation system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize validation: {e}")
            self.results.errors.append(f"Initialization error: {e}")
            return False
    
    async def run_all_validations(self) -> ValidationResults:
        """Run all validation tests"""
        logger.info("=== Starting Migration Validation ===")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return self.results
            
            # Define validation tests
            validation_tests = [
                ("Data Integrity", self.validate_data_integrity),
                ("Completeness", self.validate_completeness),
                ("Performance", self.validate_performance),
                ("Configuration", self.validate_configuration),
                ("Sessions", self.validate_sessions),
                ("Knowledge Base", self.validate_knowledge_base),
                ("Rollback Capability", self.validate_rollback_capability)
            ]
            
            # Run each validation test
            for test_name, test_func in validation_tests:
                logger.info(f"Running validation: {test_name}")
                try:
                    test_result = await test_func()
                    self.results.test_details[test_name] = test_result
                    
                    if test_result.get("status") == "passed":
                        self.results.passed += 1
                    elif test_result.get("status") == "failed":
                        self.results.failed += 1
                        self.results.errors.append(f"{test_name}: {test_result.get('error', 'Unknown error')}")
                    elif test_result.get("status") == "warning":
                        self.results.warnings += 1
                        self.results.warnings_list.append(f"{test_name}: {test_result.get('message', 'Warning')}")
                    
                    self.results.total_tests += 1
                    
                except Exception as e:
                    logger.error(f"Validation test {test_name} failed: {e}")
                    self.results.failed += 1
                    self.results.total_tests += 1
                    self.results.errors.append(f"{test_name}: {e}")
            
            # Generate final report
            await self.generate_validation_report()
            
            logger.info(f"Validation complete: {self.results.passed}/{self.results.total_tests} passed")
            return self.results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.results.errors.append(f"Validation error: {e}")
            return self.results
        
        finally:
            # Cleanup
            if self.db_manager:
                await self.db_manager.close()
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity after migration"""
        try:
            logger.info("Validating data integrity...")
            
            integrity_checks = {
                "database_connections": False,
                "table_structures": False,
                "foreign_key_constraints": False,
                "data_consistency": False,
                "checksum_validation": False
            }
            
            # Check database connections
            try:
                async with self.db_manager.get_session() as session:
                    result = await session.execute("SELECT 1")
                    if result.fetchone():
                        integrity_checks["database_connections"] = True
            except Exception as e:
                logger.error(f"Database connection check failed: {e}")
            
            # Check table structures
            try:
                async with self.db_manager.get_session() as session:
                    # Check if required tables exist
                    required_tables = ["mcp_sessions", "mcp_resources", "mcp_logs"]
                    for table in required_tables:
                        result = await session.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                        if not result.fetchone():
                            raise Exception(f"Required table {table} not found")
                    integrity_checks["table_structures"] = True
            except Exception as e:
                logger.error(f"Table structure check failed: {e}")
            
            # Check data consistency
            try:
                async with self.db_manager.get_session() as session:
                    # Check for orphaned records
                    session_count = await session.execute("SELECT COUNT(*) FROM mcp_sessions")
                    resource_count = await session.execute("SELECT COUNT(*) FROM mcp_resources")
                    
                    session_count = session_count.fetchone()[0]
                    resource_count = resource_count.fetchone()[0]
                    
                    if session_count > 0 and resource_count > 0:
                        integrity_checks["data_consistency"] = True
                    else:
                        logger.warning(f"Low data counts: sessions={session_count}, resources={resource_count}")
            except Exception as e:
                logger.error(f"Data consistency check failed: {e}")
            
            # Overall integrity score
            passed_checks = sum(integrity_checks.values())
            total_checks = len(integrity_checks)
            integrity_score = (passed_checks / total_checks) * 100
            
            if integrity_score >= 80:
                status = "passed"
            elif integrity_score >= 60:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "integrity_score": integrity_score,
                "checks": integrity_checks,
                "message": f"Data integrity: {integrity_score:.1f}% ({passed_checks}/{total_checks} checks passed)"
            }
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "integrity_score": 0
            }
    
    async def validate_completeness(self) -> Dict[str, Any]:
        """Validate migration completeness"""
        try:
            logger.info("Validating migration completeness...")
            
            completeness_data = {
                "migration_summaries_found": 0,
                "expected_summaries": len(self.migration_summaries),
                "data_volumes": {},
                "missing_components": []
            }
            
            # Check migration summary files
            for summary_file in self.migration_summaries:
                summary_path = Path(summary_file)
                if summary_path.exists():
                    completeness_data["migration_summaries_found"] += 1
                    
                    # Read summary for detailed analysis
                    try:
                        async with aiofiles.open(summary_path, 'r') as f:
                            summary = json.loads(await f.read())
                        
                        # Extract key metrics
                        stats = summary.get("statistics", {})
                        component_name = summary_file.replace("migration_summary_", "").replace(".json", "")
                        completeness_data["data_volumes"][component_name] = stats
                        
                    except Exception as e:
                        logger.warning(f"Could not read summary {summary_file}: {e}")
                else:
                    completeness_data["missing_components"].append(summary_file)
            
            # Check actual migrated data in database
            try:
                async with self.db_manager.get_session() as session:
                    # Count migrated sessions
                    session_result = await session.execute(
                        "SELECT COUNT(*) FROM mcp_sessions WHERE metadata LIKE '%migrated%'"
                    )
                    migrated_sessions = session_result.fetchone()[0]
                    
                    # Count migrated resources
                    resource_result = await session.execute(
                        "SELECT COUNT(*) FROM mcp_resources WHERE metadata LIKE '%migrated%'"
                    )
                    migrated_resources = resource_result.fetchone()[0]
                    
                    completeness_data["data_volumes"]["database_counts"] = {
                        "migrated_sessions": migrated_sessions,
                        "migrated_resources": migrated_resources
                    }
                    
            except Exception as e:
                logger.error(f"Database count check failed: {e}")
            
            # Calculate completeness score
            summary_completeness = (completeness_data["migration_summaries_found"] / completeness_data["expected_summaries"]) * 100
            
            # Determine status
            if summary_completeness >= 100 and not completeness_data["missing_components"]:
                status = "passed"
            elif summary_completeness >= 75:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "completeness_score": summary_completeness,
                "data": completeness_data,
                "message": f"Migration completeness: {summary_completeness:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"Completeness validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "completeness_score": 0
            }
    
    async def validate_performance(self) -> Dict[str, Any]:
        """Validate system performance after migration"""
        try:
            logger.info("Validating system performance...")
            
            performance_metrics = {}
            
            # Test database query performance
            start_time = datetime.datetime.now()
            async with self.db_manager.get_session() as session:
                # Run representative queries
                await session.execute("SELECT COUNT(*) FROM mcp_sessions")
                await session.execute("SELECT COUNT(*) FROM mcp_resources")
                await session.execute("SELECT * FROM mcp_sessions LIMIT 10")
            
            db_query_time = (datetime.datetime.now() - start_time).total_seconds()
            performance_metrics["database_query_time_seconds"] = db_query_time
            
            # Test session manager performance
            start_time = datetime.datetime.now()
            sessions = await self.session_manager.list_sessions(limit=10)
            session_list_time = (datetime.datetime.now() - start_time).total_seconds()
            performance_metrics["session_list_time_seconds"] = session_list_time
            
            # Test resource manager performance
            start_time = datetime.datetime.now()
            resources = await self.resource_manager.list_resources(limit=10)
            resource_list_time = (datetime.datetime.now() - start_time).total_seconds()
            performance_metrics["resource_list_time_seconds"] = resource_list_time
            
            # Calculate performance score
            max_acceptable_time = 5.0  # 5 seconds max for operations
            performance_score = 100
            
            if db_query_time > max_acceptable_time:
                performance_score -= 30
            if session_list_time > max_acceptable_time:
                performance_score -= 35
            if resource_list_time > max_acceptable_time:
                performance_score -= 35
            
            performance_score = max(0, performance_score)
            
            # Determine status
            if performance_score >= 90:
                status = "passed"
            elif performance_score >= 70:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "performance_score": performance_score,
                "metrics": performance_metrics,
                "message": f"Performance score: {performance_score}%"
            }
            
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "performance_score": 0
            }
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration migration"""
        try:
            logger.info("Validating configuration migration...")
            
            config_checks = {
                "mcp_config_loaded": False,
                "database_config_valid": False,
                "required_settings_present": False,
                "environment_variables": False
            }
            
            # Check MCP config loading
            try:
                config = load_config()
                if config.mcp.name and config.mcp.transport:
                    config_checks["mcp_config_loaded"] = True
            except Exception as e:
                logger.error(f"MCP config check failed: {e}")
            
            # Check database config
            try:
                if self.db_manager and self.db_manager.engine:
                    config_checks["database_config_valid"] = True
            except Exception as e:
                logger.error(f"Database config check failed: {e}")
            
            # Check required settings
            try:
                required_env_vars = ["SECRET_KEY", "DATABASE_URL"]
                present_vars = 0
                for var in required_env_vars:
                    if os.getenv(var):
                        present_vars += 1
                
                if present_vars >= len(required_env_vars) * 0.8:  # 80% of required vars
                    config_checks["required_settings_present"] = True
            except Exception as e:
                logger.error(f"Required settings check failed: {e}")
            
            # Check migrated environment variables
            try:
                mcp_vars = [var for var in os.environ if var.startswith("MCP_")]
                if len(mcp_vars) > 0:
                    config_checks["environment_variables"] = True
            except Exception as e:
                logger.error(f"Environment variables check failed: {e}")
            
            # Calculate config score
            passed_checks = sum(config_checks.values())
            total_checks = len(config_checks)
            config_score = (passed_checks / total_checks) * 100
            
            # Determine status
            if config_score >= 90:
                status = "passed"
            elif config_score >= 70:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "config_score": config_score,
                "checks": config_checks,
                "message": f"Configuration validation: {config_score:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "config_score": 0
            }
    
    async def validate_sessions(self) -> Dict[str, Any]:
        """Validate session migration"""
        try:
            logger.info("Validating session migration...")
            
            session_validation = {
                "total_sessions": 0,
                "migrated_sessions": 0,
                "active_sessions": 0,
                "session_types": {},
                "sample_session_valid": False
            }
            
            # Count sessions
            async with self.db_manager.get_session() as session:
                # Total sessions
                total_result = await session.execute("SELECT COUNT(*) FROM mcp_sessions")
                session_validation["total_sessions"] = total_result.fetchone()[0]
                
                # Migrated sessions
                migrated_result = await session.execute(
                    "SELECT COUNT(*) FROM mcp_sessions WHERE metadata LIKE '%migrated%'"
                )
                session_validation["migrated_sessions"] = migrated_result.fetchone()[0]
                
                # Session types
                type_result = await session.execute(
                    "SELECT metadata, COUNT(*) FROM mcp_sessions GROUP BY metadata"
                )
                for row in type_result.fetchall():
                    try:
                        metadata = json.loads(row[0])
                        session_type = metadata.get("session_type", "unknown")
                        session_validation["session_types"][session_type] = row[1]
                    except:
                        session_validation["session_types"]["unknown"] = row[1]
            
            # Test session functionality
            try:
                sessions = await self.session_manager.list_sessions(limit=1)
                if sessions:
                    test_session = sessions[0]
                    retrieved_session = await self.session_manager.get_session(test_session.session_id)
                    if retrieved_session:
                        session_validation["sample_session_valid"] = True
            except Exception as e:
                logger.error(f"Session functionality test failed: {e}")
            
            # Calculate session score
            session_score = 0
            if session_validation["total_sessions"] > 0:
                session_score += 25
            if session_validation["migrated_sessions"] > 0:
                session_score += 25
            if session_validation["sample_session_valid"]:
                session_score += 25
            if len(session_validation["session_types"]) > 0:
                session_score += 25
            
            # Determine status
            if session_score >= 90:
                status = "passed"
            elif session_score >= 70:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "session_score": session_score,
                "data": session_validation,
                "message": f"Session validation: {session_score}%"
            }
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "session_score": 0
            }
    
    async def validate_knowledge_base(self) -> Dict[str, Any]:
        """Validate knowledge base migration"""
        try:
            logger.info("Validating knowledge base migration...")
            
            knowledge_validation = {
                "total_resources": 0,
                "migrated_resources": 0,
                "knowledge_types": {},
                "sample_resource_valid": False,
                "content_integrity": False
            }
            
            # Count resources
            async with self.db_manager.get_session() as session:
                # Total resources
                total_result = await session.execute("SELECT COUNT(*) FROM mcp_resources")
                knowledge_validation["total_resources"] = total_result.fetchone()[0]
                
                # Migrated resources
                migrated_result = await session.execute(
                    "SELECT COUNT(*) FROM mcp_resources WHERE metadata LIKE '%migrated%'"
                )
                knowledge_validation["migrated_resources"] = migrated_result.fetchone()[0]
                
                # Knowledge types
                type_result = await session.execute(
                    "SELECT metadata, COUNT(*) FROM mcp_resources GROUP BY metadata"
                )
                for row in type_result.fetchall():
                    try:
                        metadata = json.loads(row[0])
                        knowledge_type = metadata.get("knowledge_type", "unknown")
                        knowledge_validation["knowledge_types"][knowledge_type] = row[1]
                    except:
                        knowledge_validation["knowledge_types"]["unknown"] = row[1]
            
            # Test resource functionality
            try:
                resources = await self.resource_manager.list_resources(limit=1)
                if resources:
                    test_resource = resources[0]
                    retrieved_resource = await self.resource_manager.get_resource(test_resource.uri)
                    if retrieved_resource and retrieved_resource.content:
                        knowledge_validation["sample_resource_valid"] = True
                        
                        # Basic content integrity check
                        if len(retrieved_resource.content) > 0:
                            knowledge_validation["content_integrity"] = True
            except Exception as e:
                logger.error(f"Resource functionality test failed: {e}")
            
            # Calculate knowledge score
            knowledge_score = 0
            if knowledge_validation["total_resources"] > 0:
                knowledge_score += 20
            if knowledge_validation["migrated_resources"] > 0:
                knowledge_score += 20
            if knowledge_validation["sample_resource_valid"]:
                knowledge_score += 20
            if knowledge_validation["content_integrity"]:
                knowledge_score += 20
            if len(knowledge_validation["knowledge_types"]) > 0:
                knowledge_score += 20
            
            # Determine status
            if knowledge_score >= 90:
                status = "passed"
            elif knowledge_score >= 70:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "knowledge_score": knowledge_score,
                "data": knowledge_validation,
                "message": f"Knowledge base validation: {knowledge_score}%"
            }
            
        except Exception as e:
            logger.error(f"Knowledge base validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "knowledge_score": 0
            }
    
    async def validate_rollback_capability(self) -> Dict[str, Any]:
        """Validate rollback capability"""
        try:
            logger.info("Validating rollback capability...")
            
            rollback_validation = {
                "backup_files_present": False,
                "backup_integrity": False,
                "rollback_scripts_available": False,
                "backup_completeness": 0
            }
            
            # Check for backup files
            backup_dir = Path("migration/backups")
            if backup_dir.exists():
                backup_files = list(backup_dir.rglob("*.backup*"))
                backup_files.extend(list(backup_dir.rglob("*backup*")))
                
                if len(backup_files) > 0:
                    rollback_validation["backup_files_present"] = True
                    rollback_validation["backup_completeness"] = len(backup_files)
                    
                    # Basic integrity check - ensure backups are readable
                    readable_backups = 0
                    for backup_file in backup_files[:5]:  # Check first 5 backups
                        try:
                            if backup_file.stat().st_size > 0:
                                readable_backups += 1
                        except:
                            pass
                    
                    if readable_backups > 0:
                        rollback_validation["backup_integrity"] = True
            
            # Check for rollback scripts
            rollback_scripts = [
                "rollback_migration.py",
                "restore_backup.py", 
                "migration_rollback.sh"
            ]
            
            available_scripts = 0
            for script in rollback_scripts:
                if Path(script).exists() or Path(f"migration/{script}").exists():
                    available_scripts += 1
            
            if available_scripts > 0:
                rollback_validation["rollback_scripts_available"] = True
            
            # Calculate rollback score
            rollback_score = 0
            if rollback_validation["backup_files_present"]:
                rollback_score += 40
            if rollback_validation["backup_integrity"]:
                rollback_score += 30
            if rollback_validation["rollback_scripts_available"]:
                rollback_score += 30
            
            # Determine status
            if rollback_score >= 70:
                status = "passed"
            elif rollback_score >= 50:
                status = "warning"
            else:
                status = "failed"
            
            return {
                "status": status,
                "rollback_score": rollback_score,
                "data": rollback_validation,
                "message": f"Rollback capability: {rollback_score}%"
            }
            
        except Exception as e:
            logger.error(f"Rollback validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "rollback_score": 0
            }
    
    async def generate_validation_report(self):
        """Generate comprehensive validation report"""
        try:
            report = {
                "validation_timestamp": datetime.datetime.utcnow().isoformat(),
                "overall_results": asdict(self.results),
                "detailed_results": self.results.test_details,
                "recommendations": [],
                "summary": {
                    "success_rate": self.results.success_rate,
                    "total_tests": self.results.total_tests,
                    "passed": self.results.passed,
                    "failed": self.results.failed,
                    "warnings": self.results.warnings
                }
            }
            
            # Generate recommendations based on results
            if self.results.success_rate >= 90:
                report["recommendations"].append("Migration validation successful - system ready for production")
            elif self.results.success_rate >= 75:
                report["recommendations"].append("Migration mostly successful - review warnings before production")
            else:
                report["recommendations"].append("Migration validation failed - address errors before production")
            
            if self.results.failed > 0:
                report["recommendations"].append("Review failed tests and consider re-running migration for failed components")
            
            if self.results.warnings > 0:
                report["recommendations"].append("Review warnings and consider improvements for optimal performance")
            
            # Save report
            report_path = Path("migration_validation_report.json")
            async with aiofiles.open(report_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report, indent=2, default=str))
            
            logger.info(f"Validation report saved: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating validation report: {e}")

async def main():
    """Main validation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate migration from claude_ai_novo to MCP system")
    parser.add_argument("--source", help="Source claude_ai_novo path")
    parser.add_argument("--target-db", help="Target database URL")
    parser.add_argument("--test", help="Run specific test only", choices=[
        "integrity", "completeness", "performance", "configuration", 
        "sessions", "knowledge", "rollback"
    ])
    
    args = parser.parse_args()
    
    validator = MigrationValidator(
        source_path=args.source,
        target_db_url=args.target_db
    )
    
    if args.test:
        # Run specific test
        test_map = {
            "integrity": validator.validate_data_integrity,
            "completeness": validator.validate_completeness,
            "performance": validator.validate_performance,
            "configuration": validator.validate_configuration,
            "sessions": validator.validate_sessions,
            "knowledge": validator.validate_knowledge_base,
            "rollback": validator.validate_rollback_capability
        }
        
        if args.test in test_map:
            await validator.initialize()
            result = await test_map[args.test]()
            print(json.dumps(result, indent=2, default=str))
    else:
        # Run all validations
        results = await validator.run_all_validations()
        print(json.dumps(asdict(results), indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())