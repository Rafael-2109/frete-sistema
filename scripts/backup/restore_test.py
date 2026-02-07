#!/usr/bin/env python3
"""
MCP Restore Test - Automated recovery testing for disaster recovery validation
Tests restore procedures in isolated environments to ensure recovery readiness
"""

import os
import sys
import json
import shutil
import tempfile
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import docker
import psycopg2
import redis

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

class RestoreTest:
    """Automated restore testing system"""
    
    def __init__(self, config_path: str = "config/backup_config.json"):
        self.config = self.load_config(config_path)
        self.logger = setup_logger("restore_test")
        self.backup_dir = Path(self.config.get("backup_dir", "/var/backups/mcp"))
        self.test_dir = Path("/tmp/mcp_restore_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Docker client for isolated testing
        self.docker_client = docker.from_env()
        
        # Test results tracking
        self.test_results = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
    
    def load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            self.logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
    
    def create_test_environment(self, test_name: str) -> Dict:
        """Create isolated test environment"""
        env_path = self.test_dir / test_name
        env_path.mkdir(parents=True, exist_ok=True)
        
        environment = {
            "name": test_name,
            "path": str(env_path),
            "containers": {},
            "networks": {},
            "volumes": {}
        }
        
        try:
            # Create test network
            network_name = f"mcp_test_{test_name}"
            network = self.docker_client.networks.create(
                network_name,
                driver="bridge"
            )
            environment["networks"]["test"] = network
            
            self.logger.info(f"Created test environment: {test_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create test environment: {e}")
            raise
        
        return environment
    
    def cleanup_test_environment(self, environment: Dict):
        """Cleanup test environment"""
        try:
            # Remove containers
            for container_name, container in environment.get("containers", {}).items():
                if hasattr(container, 'remove'):
                    self.logger.info(f"Removing container: {container_name}")
                    container.stop()
                    container.remove(force=True)
            
            # Remove networks
            for network_name, network in environment.get("networks", {}).items():
                if hasattr(network, 'remove'):
                    self.logger.info(f"Removing network: {network_name}")
                    network.remove()
            
            # Remove volumes
            for volume_name, volume in environment.get("volumes", {}).items():
                if hasattr(volume, 'remove'):
                    self.logger.info(f"Removing volume: {volume_name}")
                    volume.remove(force=True)
            
            # Remove test directory
            if "path" in environment:
                shutil.rmtree(environment["path"], ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    def setup_test_database(self, environment: Dict) -> bool:
        """Setup test PostgreSQL database"""
        try:
            # Create database volume
            volume_name = f"mcp_test_db_{environment['name']}"
            db_volume = self.docker_client.volumes.create(volume_name)
            environment["volumes"]["database"] = db_volume
            
            # Start PostgreSQL container
            container = self.docker_client.containers.run(
                "postgres:13",
                name=f"mcp_test_db_{environment['name']}",
                environment={
                    "POSTGRES_USER": "testuser",
                    "POSTGRES_PASSWORD": "testpass",
                    "POSTGRES_DB": "testdb"
                },
                volumes={
                    volume_name: {"bind": "/var/lib/postgresql/data", "mode": "rw"}
                },
                network=environment["networks"]["test"].name,
                detach=True
            )
            
            environment["containers"]["database"] = container
            
            # Wait for database to be ready
            import time
            for i in range(30):
                try:
                    conn = psycopg2.connect(
                        host="localhost",
                        port=container.ports['5432/tcp'][0]['HostPort'],
                        user="testuser",
                        password="testpass",
                        database="testdb"
                    )
                    conn.close()
                    self.logger.info("Test database ready")
                    return True
                except:
                    time.sleep(1)
            
            self.logger.error("Test database failed to start")
            return False
            
        except Exception as e:
            self.logger.error(f"Database setup error: {e}")
            return False
    
    def setup_test_redis(self, environment: Dict) -> bool:
        """Setup test Redis instance"""
        try:
            # Start Redis container
            container = self.docker_client.containers.run(
                "redis:6-alpine",
                name=f"mcp_test_redis_{environment['name']}",
                network=environment["networks"]["test"].name,
                detach=True
            )
            
            environment["containers"]["redis"] = container
            
            # Wait for Redis to be ready
            import time
            for i in range(10):
                try:
                    r = redis.Redis(
                        host="localhost",
                        port=container.ports['6379/tcp'][0]['HostPort']
                    )
                    r.ping()
                    self.logger.info("Test Redis ready")
                    return True
                except:
                    time.sleep(1)
            
            self.logger.error("Test Redis failed to start")
            return False
            
        except Exception as e:
            self.logger.error(f"Redis setup error: {e}")
            return False
    
    def test_database_restore(self, backup_name: str, environment: Dict) -> Dict:
        """Test database restoration"""
        test_result = {
            "component": "database",
            "backup": backup_name,
            "status": "unknown",
            "steps": []
        }
        
        try:
            # Setup test database
            step_result = {
                "step": "setup_database",
                "status": "unknown"
            }
            
            if self.setup_test_database(environment):
                step_result["status"] = "passed"
                step_result["message"] = "Test database created"
            else:
                step_result["status"] = "failed"
                step_result["message"] = "Failed to create test database"
                test_result["steps"].append(step_result)
                test_result["status"] = "failed"
                return test_result
            
            test_result["steps"].append(step_result)
            
            # Find backup file
            backup_path = self.backup_dir / backup_name
            db_backup = None
            for file in backup_path.glob("database.sql*"):
                db_backup = file
                break
            
            if not db_backup:
                test_result["steps"].append({
                    "step": "find_backup",
                    "status": "failed",
                    "message": "Database backup file not found"
                })
                test_result["status"] = "failed"
                return test_result
            
            # Copy and prepare backup file
            test_backup = Path(environment["path"]) / "database.sql"
            
            if db_backup.suffix == '.gz':
                import gzip
                with gzip.open(db_backup, 'rb') as f_in:
                    with open(test_backup, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(db_backup, test_backup)
            
            # Restore to test database
            container = environment["containers"]["database"]
            port = container.ports['5432/tcp'][0]['HostPort']
            
            cmd = [
                "psql",
                "-h", "localhost",
                "-p", port,
                "-U", "testuser",
                "-d", "testdb",
                "-f", str(test_backup)
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = "testpass"
            
            restore_result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True
            )
            
            if restore_result.returncode == 0:
                test_result["steps"].append({
                    "step": "restore_database",
                    "status": "passed",
                    "message": "Database restored successfully"
                })
                
                # Verify restoration
                conn = psycopg2.connect(
                    host="localhost",
                    port=port,
                    user="testuser",
                    password="testpass",
                    database="testdb"
                )
                cursor = conn.cursor()
                
                # Count tables
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                table_count = cursor.fetchone()[0]
                
                # Count total rows
                cursor.execute("""
                    SELECT SUM(n_live_tup) FROM pg_stat_user_tables
                """)
                row_count = cursor.fetchone()[0] or 0
                
                cursor.close()
                conn.close()
                
                test_result["steps"].append({
                    "step": "verify_restoration",
                    "status": "passed",
                    "message": f"Found {table_count} tables with {row_count} total rows"
                })
                
                test_result["status"] = "passed"
                
            else:
                test_result["steps"].append({
                    "step": "restore_database",
                    "status": "failed",
                    "message": f"Restore failed: {restore_result.stderr}"
                })
                test_result["status"] = "failed"
                
        except Exception as e:
            test_result["steps"].append({
                "step": "exception",
                "status": "failed",
                "message": str(e)
            })
            test_result["status"] = "failed"
        
        return test_result
    
    def test_redis_restore(self, backup_name: str, environment: Dict) -> Dict:
        """Test Redis restoration"""
        test_result = {
            "component": "redis",
            "backup": backup_name,
            "status": "unknown",
            "steps": []
        }
        
        try:
            # Setup test Redis
            if self.setup_test_redis(environment):
                test_result["steps"].append({
                    "step": "setup_redis",
                    "status": "passed",
                    "message": "Test Redis created"
                })
            else:
                test_result["steps"].append({
                    "step": "setup_redis",
                    "status": "failed",
                    "message": "Failed to create test Redis"
                })
                test_result["status"] = "failed"
                return test_result
            
            # Find backup file
            backup_path = self.backup_dir / backup_name
            redis_backup = backup_path / "redis.rdb"
            
            if not redis_backup.exists():
                test_result["steps"].append({
                    "step": "find_backup",
                    "status": "failed",
                    "message": "Redis backup file not found"
                })
                test_result["status"] = "failed"
                return test_result
            
            # Copy backup to container
            container = environment["containers"]["redis"]
            
            # Stop Redis to replace RDB file
            container.exec_run("redis-cli SHUTDOWN")
            import time
            time.sleep(2)
            
            # Copy RDB file
            with open(redis_backup, 'rb') as f:
                container.put_archive("/data", f.read())
            
            # Restart Redis
            container.restart()
            time.sleep(2)
            
            # Verify restoration
            port = container.ports['6379/tcp'][0]['HostPort']
            r = redis.Redis(host="localhost", port=port)
            
            try:
                r.ping()
                key_count = r.dbsize()
                
                test_result["steps"].append({
                    "step": "verify_restoration",
                    "status": "passed",
                    "message": f"Redis restored with {key_count} keys"
                })
                
                test_result["status"] = "passed"
                
            except Exception as e:
                test_result["steps"].append({
                    "step": "verify_restoration",
                    "status": "failed",
                    "message": f"Redis verification failed: {str(e)}"
                })
                test_result["status"] = "failed"
                
        except Exception as e:
            test_result["steps"].append({
                "step": "exception",
                "status": "failed",
                "message": str(e)
            })
            test_result["status"] = "failed"
        
        return test_result
    
    def test_filesystem_restore(self, backup_name: str, environment: Dict) -> Dict:
        """Test filesystem restoration"""
        test_result = {
            "component": "filesystem",
            "backup": backup_name,
            "status": "unknown",
            "steps": []
        }
        
        try:
            backup_path = self.backup_dir / backup_name
            test_restore_dir = Path(environment["path"]) / "filesystem"
            test_restore_dir.mkdir(parents=True, exist_ok=True)
            
            # Find filesystem archives
            archives = list(backup_path.glob("*.tar*"))
            
            if not archives:
                test_result["steps"].append({
                    "step": "find_archives",
                    "status": "failed",
                    "message": "No filesystem archives found"
                })
                test_result["status"] = "failed"
                return test_result
            
            # Restore each archive
            restored_count = 0
            for archive in archives:
                try:
                    # Skip non-filesystem archives
                    if any(x in archive.name for x in ["database", "redis", "docker"]):
                        continue
                    
                    # Extract archive
                    import tarfile
                    with tarfile.open(archive, "r:*") as tar:
                        tar.extractall(test_restore_dir)
                    
                    restored_count += 1
                    
                except Exception as e:
                    test_result["steps"].append({
                        "step": f"restore_{archive.name}",
                        "status": "failed",
                        "message": str(e)
                    })
            
            if restored_count > 0:
                # Verify restoration
                total_files = sum(1 for _ in test_restore_dir.rglob('*') if _.is_file())
                total_size = sum(f.stat().st_size for f in test_restore_dir.rglob('*') if f.is_file())
                
                test_result["steps"].append({
                    "step": "verify_restoration",
                    "status": "passed",
                    "message": f"Restored {restored_count} archives with {total_files} files ({total_size / 1024 / 1024:.2f} MB)"
                })
                
                test_result["status"] = "passed"
            else:
                test_result["status"] = "failed"
                
        except Exception as e:
            test_result["steps"].append({
                "step": "exception",
                "status": "failed",
                "message": str(e)
            })
            test_result["status"] = "failed"
        
        return test_result
    
    def test_full_restore(self, backup_name: str) -> Dict:
        """Test complete system restoration"""
        self.logger.info(f"Starting full restore test for backup: {backup_name}")
        
        test_name = f"restore_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        environment = self.create_test_environment(test_name)
        
        full_test_result = {
            "backup": backup_name,
            "test_name": test_name,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "components": []
        }
        
        try:
            # Load backup metadata
            metadata_file = self.backup_dir / backup_name / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                components_to_test = metadata.get("components", [])
            else:
                components_to_test = ["database", "redis", "filesystem"]
            
            # Test each component
            if "database" in components_to_test:
                db_result = self.test_database_restore(backup_name, environment)
                full_test_result["components"].append(db_result)
                self.test_results["tests_run"] += 1
                if db_result["status"] == "passed":
                    self.test_results["tests_passed"] += 1
                else:
                    self.test_results["tests_failed"] += 1
            
            if "redis" in components_to_test:
                redis_result = self.test_redis_restore(backup_name, environment)
                full_test_result["components"].append(redis_result)
                self.test_results["tests_run"] += 1
                if redis_result["status"] == "passed":
                    self.test_results["tests_passed"] += 1
                else:
                    self.test_results["tests_failed"] += 1
            
            if "filesystem" in components_to_test:
                fs_result = self.test_filesystem_restore(backup_name, environment)
                full_test_result["components"].append(fs_result)
                self.test_results["tests_run"] += 1
                if fs_result["status"] == "passed":
                    self.test_results["tests_passed"] += 1
                else:
                    self.test_results["tests_failed"] += 1
            
            # Determine overall status
            component_statuses = [c["status"] for c in full_test_result["components"]]
            if all(s == "passed" for s in component_statuses):
                full_test_result["status"] = "passed"
            else:
                full_test_result["status"] = "failed"
            
        finally:
            # Cleanup test environment
            self.cleanup_test_environment(environment)
        
        self.test_results["details"].append(full_test_result)
        
        return full_test_result
    
    def run_recovery_drill(self, backup_name: Optional[str] = None) -> Dict:
        """Run complete disaster recovery drill"""
        self.logger.info("Starting disaster recovery drill")
        
        # Select backup to test
        if not backup_name:
            # Use most recent backup
            backups = sorted([
                d.name for d in self.backup_dir.iterdir()
                if d.is_dir() and d.name.startswith("backup_")
            ], reverse=True)
            
            if not backups:
                self.logger.error("No backups found for testing")
                return self.test_results
            
            backup_name = backups[0]
        
        # Run full restore test
        result = self.test_full_restore(backup_name)
        
        # Generate report
        self.generate_drill_report(result)
        
        return self.test_results
    
    def generate_drill_report(self, result: Dict):
        """Generate disaster recovery drill report"""
        report = []
        report.append("=" * 80)
        report.append("Disaster Recovery Drill Report")
        report.append("=" * 80)
        report.append(f"Timestamp: {result['timestamp']}")
        report.append(f"Backup tested: {result['backup']}")
        report.append(f"Test name: {result['test_name']}")
        report.append(f"Overall status: {result.get('status', 'unknown').upper()}")
        report.append("")
        
        # Component results
        report.append("Component Test Results:")
        report.append("-" * 40)
        
        for component in result["components"]:
            report.append(f"\nComponent: {component['component']}")
            report.append(f"Status: {component['status'].upper()}")
            
            # Show steps
            for step in component["steps"]:
                status_icon = "✓" if step["status"] == "passed" else "✗"
                report.append(f"  {status_icon} {step['step']}: {step.get('message', '')}")
        
        # Summary
        report.append("")
        report.append("Summary:")
        report.append("-" * 40)
        report.append(f"Total tests run: {self.test_results['tests_run']}")
        report.append(f"Tests passed: {self.test_results['tests_passed']}")
        report.append(f"Tests failed: {self.test_results['tests_failed']}")
        report.append(f"Success rate: {self.test_results['tests_passed'] / max(self.test_results['tests_run'], 1) * 100:.1f}%")
        
        # Save report
        report_file = self.test_dir / f"drill_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write("\n".join(report))
        
        self.logger.info(f"Drill report saved to: {report_file}")
        
        # Print report
        print("\n".join(report))
    
    def schedule_recovery_drills(self):
        """Schedule regular recovery drills"""
        drill_schedule = """
# MCP Disaster Recovery Drill Schedule
# Run recovery drill every month on the 15th at 3 AM
0 3 15 * * /usr/bin/python3 {script_path} --drill

# Run quick restore test every week on Sunday at 4 AM
0 4 * * 0 /usr/bin/python3 {script_path} --test latest
""".format(script_path=os.path.abspath(__file__))
        
        print("Add the following to your crontab for regular recovery drills:")
        print(drill_schedule)

def main():
    parser = argparse.ArgumentParser(description="MCP Restore Testing")
    parser.add_argument("--test", help="Test restore for specific backup")
    parser.add_argument("--drill", action="store_true", 
                       help="Run full disaster recovery drill")
    parser.add_argument("--schedule", action="store_true",
                       help="Show cron schedule for regular drills")
    parser.add_argument("--config", default="config/backup_config.json",
                       help="Configuration file path")
    
    args = parser.parse_args()
    
    tester = RestoreTest(args.config)
    
    if args.drill:
        results = tester.run_recovery_drill()
        sys.exit(0 if results["tests_failed"] == 0 else 1)
    
    elif args.test:
        backup_name = args.test
        if backup_name == "latest":
            # Find latest backup
            backups = sorted([
                d.name for d in tester.backup_dir.iterdir()
                if d.is_dir() and d.name.startswith("backup_")
            ], reverse=True)
            
            if backups:
                backup_name = backups[0]
            else:
                print("No backups found")
                sys.exit(1)
        
        result = tester.test_full_restore(backup_name)
        tester.generate_drill_report(result)
        
        sys.exit(0 if result.get("status") == "passed" else 1)
    
    elif args.schedule:
        tester.schedule_recovery_drills()
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()