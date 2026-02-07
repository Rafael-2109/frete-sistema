#!/usr/bin/env python3
"""
MCP Backup Manager - Automated backup system for MCP components
Handles full and incremental backups with rotation and cloud storage
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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import NoCredentialsError
import redis
import psycopg2
from cryptography.fernet import Fernet

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

class BackupManager:
    """Comprehensive backup manager for MCP system"""
    
    def __init__(self, config_path: str = "config/backup_config.json"):
        self.config = self.load_config(config_path)
        self.logger = setup_logger("backup_manager")
        self.backup_dir = Path(self.config.get("backup_dir", "/var/backups/mcp"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption if enabled
        self.cipher = None
        if self.config.get("encryption", {}).get("enabled", False):
            self.cipher = Fernet(self.config["encryption"]["key"].encode())
        
        # Initialize cloud storage if configured
        self.s3_client = None
        if self.config.get("cloud_storage", {}).get("enabled", False):
            self.init_s3_client()
    
    def load_config(self, config_path: str) -> Dict:
        """Load backup configuration"""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config
            default_config = {
                "backup_dir": "/var/backups/mcp",
                "retention_days": 30,
                "compression": "gz",
                "encryption": {
                    "enabled": False,
                    "key": Fernet.generate_key().decode()
                },
                "cloud_storage": {
                    "enabled": False,
                    "provider": "s3",
                    "bucket": "mcp-backups",
                    "region": "us-east-1"
                },
                "components": {
                    "database": {
                        "enabled": True,
                        "type": "postgresql",
                        "connection": {
                            "host": "localhost",
                            "port": 5432,
                            "database": "frete_system",
                            "user": "postgres"
                        }
                    },
                    "redis": {
                        "enabled": True,
                        "host": "localhost",
                        "port": 6379,
                        "db": 0
                    },
                    "filesystem": {
                        "enabled": True,
                        "paths": [
                            "/app/config",
                            "/app/logs",
                            "/app/data"
                        ],
                        "exclude": [
                            "*.tmp",
                            "*.log",
                            "__pycache__"
                        ]
                    },
                    "docker": {
                        "enabled": True,
                        "containers": ["mcp-api", "mcp-worker", "mcp-scheduler"]
                    }
                },
                "schedule": {
                    "full_backup": "0 2 * * 0",  # Sunday 2 AM
                    "incremental": "0 2 * * 1-6"  # Mon-Sat 2 AM
                }
            }
            
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def init_s3_client(self):
        """Initialize S3 client for cloud storage"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.config["cloud_storage"]["region"]
            )
            self.logger.info("S3 client initialized successfully")
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            self.s3_client = None
    
    def create_backup_metadata(self, backup_type: str, components: List[str]) -> Dict:
        """Create metadata for backup"""
        return {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "type": backup_type,
            "components": components,
            "version": "1.0",
            "encryption": self.cipher is not None,
            "compression": self.config.get("compression", "gz"),
            "hostname": os.uname().nodename
        }
    
    def backup_database(self, backup_path: Path) -> bool:
        """Backup PostgreSQL database"""
        if not self.config["components"]["database"]["enabled"]:
            return True
        
        try:
            db_config = self.config["components"]["database"]["connection"]
            db_backup_file = backup_path / "database.sql"
            
            # Create pg_dump command
            cmd = [
                "pg_dump",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["user"],
                "-d", db_config["database"],
                "-f", str(db_backup_file),
                "--verbose",
                "--no-password"
            ]
            
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config.get("password", "")
            
            self.logger.info(f"Backing up database to {db_backup_file}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Database backup failed: {result.stderr}")
                return False
            
            # Compress the backup
            self.compress_file(db_backup_file)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database backup error: {e}")
            return False
    
    def backup_redis(self, backup_path: Path) -> bool:
        """Backup Redis data"""
        if not self.config["components"]["redis"]["enabled"]:
            return True
        
        try:
            redis_config = self.config["components"]["redis"]
            r = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"]
            )
            
            # Force Redis to save
            self.logger.info("Creating Redis snapshot")
            r.bgsave()
            
            # Wait for save to complete
            while r.lastsave() == r.lastsave():
                import time
                time.sleep(0.1)
            
            # Copy RDB file
            rdb_path = "/var/lib/redis/dump.rdb"
            if os.path.exists(rdb_path):
                shutil.copy2(rdb_path, backup_path / "redis.rdb")
                self.logger.info("Redis backup completed")
                return True
            else:
                self.logger.error("Redis RDB file not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Redis backup error: {e}")
            return False
    
    def backup_filesystem(self, backup_path: Path, incremental: bool = False) -> bool:
        """Backup filesystem paths"""
        if not self.config["components"]["filesystem"]["enabled"]:
            return True
        
        try:
            fs_config = self.config["components"]["filesystem"]
            
            for path in fs_config["paths"]:
                if not os.path.exists(path):
                    self.logger.warning(f"Path not found: {path}")
                    continue
                
                # Create tar archive
                archive_name = f"{Path(path).name}.tar.{self.config.get('compression', 'gz')}"
                archive_path = backup_path / archive_name
                
                self.logger.info(f"Backing up {path} to {archive_path}")
                
                with tarfile.open(archive_path, f"w:{self.config.get('compression', 'gz')}") as tar:
                    tar.add(path, arcname=Path(path).name, 
                           filter=self._tar_filter)
                
                # Encrypt if enabled
                if self.cipher:
                    self.encrypt_file(archive_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Filesystem backup error: {e}")
            return False
    
    def _tar_filter(self, tarinfo):
        """Filter function for tar archive"""
        exclude_patterns = self.config["components"]["filesystem"]["exclude"]
        for pattern in exclude_patterns:
            if pattern in tarinfo.name:
                return None
        return tarinfo
    
    def backup_docker_containers(self, backup_path: Path) -> bool:
        """Backup Docker containers"""
        if not self.config["components"]["docker"]["enabled"]:
            return True
        
        try:
            containers = self.config["components"]["docker"]["containers"]
            
            for container in containers:
                self.logger.info(f"Backing up Docker container: {container}")
                
                # Export container
                export_file = backup_path / f"{container}.tar"
                cmd = ["docker", "export", "-o", str(export_file), container]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Container export failed: {result.stderr}")
                    continue
                
                # Compress the export
                self.compress_file(export_file)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Docker backup error: {e}")
            return False
    
    def compress_file(self, file_path: Path):
        """Compress a file"""
        import gzip
        
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        file_path.unlink()
        
        return compressed_path
    
    def encrypt_file(self, file_path: Path):
        """Encrypt a file"""
        if not self.cipher:
            return
        
        with open(file_path, 'rb') as f:
            encrypted_data = self.cipher.encrypt(f.read())
        
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Remove original file
        file_path.unlink()
        
        return encrypted_path
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def upload_to_cloud(self, backup_path: Path):
        """Upload backup to cloud storage"""
        if not self.s3_client:
            return
        
        try:
            bucket = self.config["cloud_storage"]["bucket"]
            
            for file in backup_path.glob("**/*"):
                if file.is_file():
                    key = f"backups/{backup_path.name}/{file.relative_to(backup_path)}"
                    self.logger.info(f"Uploading {file} to s3://{bucket}/{key}")
                    
                    self.s3_client.upload_file(
                        str(file),
                        bucket,
                        key,
                        ExtraArgs={
                            'ServerSideEncryption': 'AES256',
                            'StorageClass': 'STANDARD_IA'
                        }
                    )
            
            self.logger.info("Cloud upload completed")
            
        except Exception as e:
            self.logger.error(f"Cloud upload error: {e}")
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        retention_days = self.config.get("retention_days", 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        self.logger.info(f"Cleaning up backups older than {retention_days} days")
        
        for backup in self.backup_dir.iterdir():
            if backup.is_dir():
                # Parse timestamp from directory name
                try:
                    timestamp_str = backup.name.split('_')[1]
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    
                    if backup_date < cutoff_date:
                        self.logger.info(f"Removing old backup: {backup}")
                        shutil.rmtree(backup)
                        
                except Exception as e:
                    self.logger.warning(f"Could not parse backup date: {backup.name}")
    
    def perform_backup(self, backup_type: str = "full") -> bool:
        """Perform complete backup"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_name = f"backup_{timestamp}_{backup_type}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Starting {backup_type} backup: {backup_name}")
        
        # Track which components were backed up
        backed_up_components = []
        success = True
        
        # Backup database
        if self.backup_database(backup_path):
            backed_up_components.append("database")
        else:
            success = False
        
        # Backup Redis
        if self.backup_redis(backup_path):
            backed_up_components.append("redis")
        else:
            success = False
        
        # Backup filesystem
        if self.backup_filesystem(backup_path, incremental=(backup_type == "incremental")):
            backed_up_components.append("filesystem")
        else:
            success = False
        
        # Backup Docker containers
        if self.backup_docker_containers(backup_path):
            backed_up_components.append("docker")
        else:
            success = False
        
        # Create metadata file
        metadata = self.create_backup_metadata(backup_type, backed_up_components)
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create checksums
        checksums = {}
        for file in backup_path.glob("**/*"):
            if file.is_file():
                checksums[str(file.relative_to(backup_path))] = self.calculate_checksum(file)
        
        with open(backup_path / "checksums.json", 'w') as f:
            json.dump(checksums, f, indent=2)
        
        # Upload to cloud if configured
        if self.config.get("cloud_storage", {}).get("enabled", False):
            self.upload_to_cloud(backup_path)
        
        # Cleanup old backups
        self.cleanup_old_backups()
        
        if success:
            self.logger.info(f"Backup completed successfully: {backup_name}")
        else:
            self.logger.warning(f"Backup completed with errors: {backup_name}")
        
        return success
    
    def list_backups(self) -> List[Dict]:
        """List available backups"""
        backups = []
        
        for backup in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup.is_dir() and (backup / "metadata.json").exists():
                with open(backup / "metadata.json", 'r') as f:
                    metadata = json.load(f)
                
                # Calculate backup size
                size = sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
                
                backups.append({
                    "name": backup.name,
                    "path": str(backup),
                    "timestamp": metadata["timestamp"],
                    "type": metadata["type"],
                    "components": metadata["components"],
                    "size": size,
                    "encrypted": metadata.get("encryption", False)
                })
        
        return backups

def main():
    parser = argparse.ArgumentParser(description="MCP Backup Manager")
    parser.add_argument("action", choices=["backup", "list", "cleanup"],
                       help="Action to perform")
    parser.add_argument("--type", choices=["full", "incremental"], default="full",
                       help="Backup type")
    parser.add_argument("--config", default="config/backup_config.json",
                       help="Configuration file path")
    
    args = parser.parse_args()
    
    manager = BackupManager(args.config)
    
    if args.action == "backup":
        success = manager.perform_backup(args.type)
        sys.exit(0 if success else 1)
    
    elif args.action == "list":
        backups = manager.list_backups()
        
        print(f"\nAvailable backups in {manager.backup_dir}:")
        print("-" * 80)
        
        for backup in backups:
            print(f"\n{backup['name']}")
            print(f"  Timestamp: {backup['timestamp']}")
            print(f"  Type: {backup['type']}")
            print(f"  Components: {', '.join(backup['components'])}")
            print(f"  Size: {backup['size'] / 1024 / 1024:.2f} MB")
            print(f"  Encrypted: {backup['encrypted']}")
    
    elif args.action == "cleanup":
        manager.cleanup_old_backups()
        print("Cleanup completed")

if __name__ == "__main__":
    main()