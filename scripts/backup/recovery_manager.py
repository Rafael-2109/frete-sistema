#!/usr/bin/env python3
"""
MCP Recovery Manager - Disaster recovery system for MCP components
Handles restoration from backups with verification and rollback capabilities
"""

import os
import sys
import json
import shutil
import tarfile
import hashlib
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
import redis
from cryptography.fernet import Fernet
import boto3

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from app.utils.timezone import agora_utc_naive

class RecoveryManager:
    """Comprehensive recovery manager for MCP system"""
    
    def __init__(self, config_path: str = "config/backup_config.json"):
        self.config = self.load_config(config_path)
        self.logger = setup_logger("recovery_manager")
        self.backup_dir = Path(self.config.get("backup_dir", "/var/backups/mcp"))
        self.restore_dir = Path(self.config.get("restore_dir", "/var/restore/mcp"))
        self.restore_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize decryption if enabled
        self.cipher = None
        if self.config.get("encryption", {}).get("enabled", False):
            self.cipher = Fernet(self.config["encryption"]["key"].encode())
        
        # Initialize cloud storage if configured
        self.s3_client = None
        if self.config.get("cloud_storage", {}).get("enabled", False):
            self.init_s3_client()
        
        # Recovery state tracking
        self.recovery_state = {
            "started_at": None,
            "backup_name": None,
            "restored_components": [],
            "failed_components": [],
            "rollback_points": {}
        }
    
    def load_config(self, config_path: str) -> Dict:
        """Load recovery configuration"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            self.logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
    
    def init_s3_client(self):
        """Initialize S3 client for cloud storage"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.config["cloud_storage"]["region"]
            )
            self.logger.info("S3 client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def download_from_cloud(self, backup_name: str) -> bool:
        """Download backup from cloud storage"""
        if not self.s3_client:
            return False
        
        try:
            bucket = self.config["cloud_storage"]["bucket"]
            prefix = f"backups/{backup_name}/"
            local_path = self.backup_dir / backup_name
            local_path.mkdir(parents=True, exist_ok=True)
            
            # List and download all objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        relative_path = key.replace(prefix, '')
                        local_file = local_path / relative_path
                        
                        local_file.parent.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"Downloading {key} to {local_file}")
                        self.s3_client.download_file(bucket, key, str(local_file))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cloud download error: {e}")
            return False
    
    def verify_checksums(self, backup_path: Path) -> bool:
        """Verify backup integrity using checksums"""
        checksum_file = backup_path / "checksums.json"
        if not checksum_file.exists():
            self.logger.warning("No checksum file found, skipping verification")
            return True
        
        with open(checksum_file, 'r') as f:
            expected_checksums = json.load(f)
        
        self.logger.info("Verifying backup integrity...")
        
        for file_path, expected_checksum in expected_checksums.items():
            if file_path == "checksums.json":
                continue
            
            full_path = backup_path / file_path
            if not full_path.exists():
                self.logger.error(f"Missing file: {file_path}")
                return False
            
            actual_checksum = self.calculate_checksum(full_path)
            if actual_checksum != expected_checksum:
                self.logger.error(f"Checksum mismatch for {file_path}")
                return False
        
        self.logger.info("Backup integrity verified successfully")
        return True
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def decrypt_file(self, file_path: Path) -> Path:
        """Decrypt a file"""
        if not self.cipher or not file_path.suffix == '.enc':
            return file_path
        
        with open(file_path, 'rb') as f:
            decrypted_data = self.cipher.decrypt(f.read())
        
        decrypted_path = file_path.with_suffix('')
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)
        
        return decrypted_path
    
    def decompress_file(self, file_path: Path) -> Path:
        """Decompress a file"""
        import gzip
        
        if file_path.suffix != '.gz':
            return file_path
        
        decompressed_path = file_path.with_suffix('')
        
        with gzip.open(file_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_path
    
    def create_rollback_point(self, component: str) -> Dict:
        """Create a rollback point before restoration"""
        rollback_dir = self.restore_dir / "rollback" / component
        rollback_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = agora_utc_naive().strftime("%Y%m%d%H%M%S")
        rollback_point = {
            "timestamp": timestamp,
            "component": component,
            "path": str(rollback_dir / timestamp)
        }
        
        self.logger.info(f"Creating rollback point for {component}")
        
        # Component-specific rollback logic
        if component == "database":
            self.create_database_rollback(rollback_point["path"])
        elif component == "redis":
            self.create_redis_rollback(rollback_point["path"])
        elif component == "filesystem":
            self.create_filesystem_rollback(rollback_point["path"])
        
        return rollback_point
    
    def create_database_rollback(self, rollback_path: str):
        """Create database rollback point"""
        try:
            db_config = self.config["components"]["database"]["connection"]
            rollback_file = Path(rollback_path) / "database_rollback.sql"
            rollback_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                "pg_dump",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["user"],
                "-d", db_config["database"],
                "-f", str(rollback_file)
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config.get("password", "")
            
            subprocess.run(cmd, env=env, check=True)
            self.logger.info(f"Database rollback point created: {rollback_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create database rollback: {e}")
    
    def create_redis_rollback(self, rollback_path: str):
        """Create Redis rollback point"""
        try:
            redis_config = self.config["components"]["redis"]
            r = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"]
            )
            
            # Force save and copy RDB file
            r.bgsave()
            import time
            while r.lastsave() == r.lastsave():
                time.sleep(0.1)
            
            rdb_path = "/var/lib/redis/dump.rdb"
            if os.path.exists(rdb_path):
                rollback_file = Path(rollback_path) / "redis_rollback.rdb"
                rollback_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rdb_path, rollback_file)
                self.logger.info(f"Redis rollback point created: {rollback_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to create Redis rollback: {e}")
    
    def create_filesystem_rollback(self, rollback_path: str):
        """Create filesystem rollback point"""
        try:
            fs_config = self.config["components"]["filesystem"]
            rollback_dir = Path(rollback_path)
            rollback_dir.mkdir(parents=True, exist_ok=True)
            
            for path in fs_config["paths"]:
                if os.path.exists(path):
                    archive_name = f"{Path(path).name}_rollback.tar.gz"
                    archive_path = rollback_dir / archive_name
                    
                    with tarfile.open(archive_path, "w:gz") as tar:
                        tar.add(path, arcname=Path(path).name)
                    
                    self.logger.info(f"Filesystem rollback created: {archive_path}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create filesystem rollback: {e}")
    
    def restore_database(self, backup_path: Path) -> bool:
        """Restore PostgreSQL database"""
        try:
            db_backup = None
            
            # Find database backup file
            for file in backup_path.glob("database.sql*"):
                db_backup = file
                break
            
            if not db_backup:
                self.logger.error("Database backup file not found")
                return False
            
            # Decrypt if needed
            db_backup = self.decrypt_file(db_backup)
            
            # Decompress if needed
            db_backup = self.decompress_file(db_backup)
            
            db_config = self.config["components"]["database"]["connection"]
            
            # Create rollback point
            rollback_point = self.create_rollback_point("database")
            self.recovery_state["rollback_points"]["database"] = rollback_point
            
            # Drop and recreate database
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config.get("password", ""),
                database="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            db_name = db_config["database"]
            self.logger.info(f"Dropping database {db_name}")
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            
            self.logger.info(f"Creating database {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")
            
            cursor.close()
            conn.close()
            
            # Restore from backup
            cmd = [
                "psql",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["user"],
                "-d", db_config["database"],
                "-f", str(db_backup)
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config.get("password", "")
            
            self.logger.info("Restoring database from backup")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Database restore failed: {result.stderr}")
                return False
            
            self.logger.info("Database restored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Database restore error: {e}")
            return False
    
    def restore_redis(self, backup_path: Path) -> bool:
        """Restore Redis data"""
        try:
            redis_backup = backup_path / "redis.rdb"
            if not redis_backup.exists():
                self.logger.error("Redis backup file not found")
                return False
            
            # Create rollback point
            rollback_point = self.create_rollback_point("redis")
            self.recovery_state["rollback_points"]["redis"] = rollback_point
            
            redis_config = self.config["components"]["redis"]
            r = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"]
            )
            
            # Stop Redis to replace RDB file
            self.logger.info("Stopping Redis service")
            subprocess.run(["systemctl", "stop", "redis"], check=True)
            
            # Replace RDB file
            rdb_path = "/var/lib/redis/dump.rdb"
            shutil.copy2(redis_backup, rdb_path)
            
            # Set correct permissions
            subprocess.run(["chown", "redis:redis", rdb_path], check=True)
            
            # Start Redis
            self.logger.info("Starting Redis service")
            subprocess.run(["systemctl", "start", "redis"], check=True)
            
            # Verify restoration
            import time
            time.sleep(2)  # Wait for Redis to start
            
            try:
                r.ping()
                self.logger.info("Redis restored successfully")
                return True
            except:
                self.logger.error("Redis restoration verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Redis restore error: {e}")
            return False
    
    def restore_filesystem(self, backup_path: Path) -> bool:
        """Restore filesystem paths"""
        try:
            fs_config = self.config["components"]["filesystem"]
            
            # Create rollback point
            rollback_point = self.create_rollback_point("filesystem")
            self.recovery_state["rollback_points"]["filesystem"] = rollback_point
            
            for path in fs_config["paths"]:
                archive_pattern = f"{Path(path).name}.tar*"
                archives = list(backup_path.glob(archive_pattern))
                
                if not archives:
                    self.logger.warning(f"No backup found for {path}")
                    continue
                
                archive = archives[0]
                
                # Decrypt if needed
                archive = self.decrypt_file(archive)
                
                # Clear existing directory
                if os.path.exists(path):
                    self.logger.info(f"Clearing existing directory: {path}")
                    shutil.rmtree(path)
                
                # Create parent directory
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                
                # Extract archive
                self.logger.info(f"Restoring {path} from {archive}")
                
                with tarfile.open(archive, "r:*") as tar:
                    tar.extractall(Path(path).parent)
                
                self.logger.info(f"Filesystem path restored: {path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Filesystem restore error: {e}")
            return False
    
    def restore_docker_containers(self, backup_path: Path) -> bool:
        """Restore Docker containers"""
        try:
            containers = self.config["components"]["docker"]["containers"]
            
            for container in containers:
                export_pattern = f"{container}.tar*"
                exports = list(backup_path.glob(export_pattern))
                
                if not exports:
                    self.logger.warning(f"No backup found for container {container}")
                    continue
                
                export_file = exports[0]
                
                # Decompress if needed
                if export_file.suffix == '.gz':
                    export_file = self.decompress_file(export_file)
                
                # Stop existing container
                self.logger.info(f"Stopping container: {container}")
                subprocess.run(["docker", "stop", container], capture_output=True)
                subprocess.run(["docker", "rm", container], capture_output=True)
                
                # Import container
                self.logger.info(f"Importing container: {container}")
                cmd = ["docker", "import", str(export_file), f"{container}:restored"]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Container import failed: {result.stderr}")
                    continue
                
                self.logger.info(f"Container restored: {container}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Docker restore error: {e}")
            return False
    
    def rollback_component(self, component: str) -> bool:
        """Rollback a specific component to pre-restore state"""
        if component not in self.recovery_state["rollback_points"]:
            self.logger.error(f"No rollback point found for {component}")
            return False
        
        rollback_point = self.recovery_state["rollback_points"][component]
        self.logger.info(f"Rolling back {component} to {rollback_point['timestamp']}")
        
        try:
            if component == "database":
                return self.rollback_database(rollback_point["path"])
            elif component == "redis":
                return self.rollback_redis(rollback_point["path"])
            elif component == "filesystem":
                return self.rollback_filesystem(rollback_point["path"])
            else:
                self.logger.error(f"Unknown component: {component}")
                return False
                
        except Exception as e:
            self.logger.error(f"Rollback error for {component}: {e}")
            return False
    
    def rollback_database(self, rollback_path: str) -> bool:
        """Rollback database to previous state"""
        rollback_file = Path(rollback_path) / "database_rollback.sql"
        if not rollback_file.exists():
            return False
        
        db_config = self.config["components"]["database"]["connection"]
        
        cmd = [
            "psql",
            "-h", db_config["host"],
            "-p", str(db_config["port"]),
            "-U", db_config["user"],
            "-d", db_config["database"],
            "-f", str(rollback_file)
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = db_config.get("password", "")
        
        result = subprocess.run(cmd, env=env, capture_output=True)
        return result.returncode == 0
    
    def rollback_redis(self, rollback_path: str) -> bool:
        """Rollback Redis to previous state"""
        rollback_file = Path(rollback_path) / "redis_rollback.rdb"
        if not rollback_file.exists():
            return False
        
        subprocess.run(["systemctl", "stop", "redis"], check=True)
        shutil.copy2(rollback_file, "/var/lib/redis/dump.rdb")
        subprocess.run(["chown", "redis:redis", "/var/lib/redis/dump.rdb"], check=True)
        subprocess.run(["systemctl", "start", "redis"], check=True)
        
        return True
    
    def rollback_filesystem(self, rollback_path: str) -> bool:
        """Rollback filesystem to previous state"""
        rollback_dir = Path(rollback_path)
        
        for archive in rollback_dir.glob("*_rollback.tar.gz"):
            path_name = archive.stem.replace("_rollback", "")
            
            # Find original path in config
            for path in self.config["components"]["filesystem"]["paths"]:
                if Path(path).name == path_name:
                    if os.path.exists(path):
                        shutil.rmtree(path)
                    
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    
                    with tarfile.open(archive, "r:gz") as tar:
                        tar.extractall(Path(path).parent)
                    
                    break
        
        return True
    
    def perform_recovery(self, backup_name: str, components: Optional[List[str]] = None) -> bool:
        """Perform complete recovery from backup"""
        self.recovery_state["started_at"] = agora_utc_naive()
        self.recovery_state["backup_name"] = backup_name
        
        # Find backup
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            self.logger.info(f"Backup not found locally, checking cloud storage...")
            if self.s3_client and self.download_from_cloud(backup_name):
                self.logger.info("Backup downloaded from cloud storage")
            else:
                self.logger.error(f"Backup not found: {backup_name}")
                return False
        
        # Load metadata
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            self.logger.error("Backup metadata not found")
            return False
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.logger.info(f"Starting recovery from backup: {backup_name}")
        self.logger.info(f"Backup timestamp: {metadata['timestamp']}")
        self.logger.info(f"Backup type: {metadata['type']}")
        
        # Verify backup integrity
        if not self.verify_checksums(backup_path):
            self.logger.error("Backup verification failed")
            return False
        
        # Determine which components to restore
        if components:
            restore_components = [c for c in components if c in metadata["components"]]
        else:
            restore_components = metadata["components"]
        
        self.logger.info(f"Components to restore: {', '.join(restore_components)}")
        
        # Restore each component
        success = True
        
        if "database" in restore_components:
            if self.restore_database(backup_path):
                self.recovery_state["restored_components"].append("database")
            else:
                self.recovery_state["failed_components"].append("database")
                success = False
        
        if "redis" in restore_components:
            if self.restore_redis(backup_path):
                self.recovery_state["restored_components"].append("redis")
            else:
                self.recovery_state["failed_components"].append("redis")
                success = False
        
        if "filesystem" in restore_components:
            if self.restore_filesystem(backup_path):
                self.recovery_state["restored_components"].append("filesystem")
            else:
                self.recovery_state["failed_components"].append("filesystem")
                success = False
        
        if "docker" in restore_components:
            if self.restore_docker_containers(backup_path):
                self.recovery_state["restored_components"].append("docker")
            else:
                self.recovery_state["failed_components"].append("docker")
                success = False
        
        # Save recovery state
        state_file = self.restore_dir / f"recovery_state_{agora_utc_naive().strftime('%Y%m%d%H%M%S')}.json"
        with open(state_file, 'w') as f:
            json.dump(self.recovery_state, f, indent=2, default=str)
        
        if success:
            self.logger.info("Recovery completed successfully")
        else:
            self.logger.warning("Recovery completed with errors")
            self.logger.info(f"Failed components: {', '.join(self.recovery_state['failed_components'])}")
        
        return success

def main():
    parser = argparse.ArgumentParser(description="MCP Recovery Manager")
    parser.add_argument("action", choices=["restore", "rollback", "verify"],
                       help="Action to perform")
    parser.add_argument("--backup", help="Backup name to restore from")
    parser.add_argument("--components", nargs="+", 
                       choices=["database", "redis", "filesystem", "docker"],
                       help="Specific components to restore")
    parser.add_argument("--config", default="config/backup_config.json",
                       help="Configuration file path")
    
    args = parser.parse_args()
    
    manager = RecoveryManager(args.config)
    
    if args.action == "restore":
        if not args.backup:
            print("Error: --backup is required for restore action")
            sys.exit(1)
        
        success = manager.perform_recovery(args.backup, args.components)
        sys.exit(0 if success else 1)
    
    elif args.action == "rollback":
        if not args.components:
            print("Error: --components is required for rollback action")
            sys.exit(1)
        
        success = True
        for component in args.components:
            if not manager.rollback_component(component):
                success = False
        
        sys.exit(0 if success else 1)
    
    elif args.action == "verify":
        if not args.backup:
            print("Error: --backup is required for verify action")
            sys.exit(1)
        
        backup_path = manager.backup_dir / args.backup
        if not backup_path.exists():
            print(f"Backup not found: {args.backup}")
            sys.exit(1)
        
        if manager.verify_checksums(backup_path):
            print("Backup verification successful")
            sys.exit(0)
        else:
            print("Backup verification failed")
            sys.exit(1)

if __name__ == "__main__":
    main()