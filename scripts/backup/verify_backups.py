#!/usr/bin/env python3
"""
MCP Backup Verification - Integrity checks and validation for backups
Ensures backup reliability and detects corruption or missing files
"""

import os
import sys
import json
import hashlib
import tarfile
import gzip
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import psycopg2
import redis
from cryptography.fernet import Fernet

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from app.utils.timezone import agora_utc_naive

class BackupVerifier:
    """Comprehensive backup verification system"""
    
    def __init__(self, config_path: str = "config/backup_config.json"):
        self.config = self.load_config(config_path)
        self.logger = setup_logger("backup_verifier")
        self.backup_dir = Path(self.config.get("backup_dir", "/var/backups/mcp"))
        self.verification_results = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "backups_verified": 0,
            "backups_passed": 0,
            "backups_failed": 0,
            "issues": []
        }
        
        # Initialize decryption if enabled
        self.cipher = None
        if self.config.get("encryption", {}).get("enabled", False):
            self.cipher = Fernet(self.config["encryption"]["key"].encode())
    
    def load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            self.logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_file_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum matches expected value"""
        try:
            actual_checksum = self.calculate_checksum(file_path)
            return actual_checksum == expected_checksum
        except Exception as e:
            self.logger.error(f"Error calculating checksum for {file_path}: {e}")
            return False
    
    def verify_encrypted_file(self, file_path: Path) -> Tuple[bool, str]:
        """Verify encrypted file can be decrypted"""
        if not self.cipher or not file_path.suffix == '.enc':
            return True, "Not encrypted"
        
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Try to decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Basic validation - check if decrypted data is valid
            if len(decrypted_data) > 0:
                return True, "Decryption successful"
            else:
                return False, "Decrypted data is empty"
                
        except Exception as e:
            return False, f"Decryption failed: {str(e)}"
    
    def verify_compressed_file(self, file_path: Path) -> Tuple[bool, str]:
        """Verify compressed file integrity"""
        if file_path.suffix == '.gz':
            try:
                with gzip.open(file_path, 'rb') as f:
                    # Try to read some data to verify integrity
                    f.read(1024)
                return True, "Compression valid"
            except Exception as e:
                return False, f"Decompression failed: {str(e)}"
        
        elif file_path.suffix in ['.tar', '.tgz', '.tar.gz']:
            try:
                with tarfile.open(file_path, 'r:*') as tar:
                    # Check if we can read the file list
                    tar.getnames()
                return True, "Archive valid"
            except Exception as e:
                return False, f"Archive corrupted: {str(e)}"
        
        return True, "Not compressed"
    
    def verify_database_backup(self, backup_path: Path) -> Dict:
        """Verify database backup integrity"""
        results = {
            "component": "database",
            "status": "unknown",
            "checks": []
        }
        
        # Find database backup file
        db_files = list(backup_path.glob("database.sql*"))
        if not db_files:
            results["status"] = "failed"
            results["checks"].append({
                "check": "file_exists",
                "passed": False,
                "message": "Database backup file not found"
            })
            return results
        
        db_file = db_files[0]
        
        # Check file size
        file_size = db_file.stat().st_size
        if file_size == 0:
            results["checks"].append({
                "check": "file_size",
                "passed": False,
                "message": "Database backup file is empty"
            })
        else:
            results["checks"].append({
                "check": "file_size",
                "passed": True,
                "message": f"File size: {file_size / 1024 / 1024:.2f} MB"
            })
        
        # Verify encryption if applicable
        if db_file.suffix == '.enc':
            passed, message = self.verify_encrypted_file(db_file)
            results["checks"].append({
                "check": "encryption",
                "passed": passed,
                "message": message
            })
        
        # Verify compression if applicable
        if db_file.suffix in ['.gz', '.bz2']:
            passed, message = self.verify_compressed_file(db_file)
            results["checks"].append({
                "check": "compression",
                "passed": passed,
                "message": message
            })
        
        # Check SQL syntax (basic validation)
        if db_file.suffix == '.sql' or (db_file.suffix == '.gz' and '.sql' in db_file.stem):
            try:
                # Read first few lines to check SQL header
                if db_file.suffix == '.gz':
                    with gzip.open(db_file, 'rt') as f:
                        header = f.read(1000)
                else:
                    with open(db_file, 'r') as f:
                        header = f.read(1000)
                
                if "PostgreSQL" in header or "CREATE TABLE" in header:
                    results["checks"].append({
                        "check": "sql_syntax",
                        "passed": True,
                        "message": "SQL header validation passed"
                    })
                else:
                    results["checks"].append({
                        "check": "sql_syntax",
                        "passed": False,
                        "message": "SQL header validation failed"
                    })
                    
            except Exception as e:
                results["checks"].append({
                    "check": "sql_syntax",
                    "passed": False,
                    "message": f"SQL validation error: {str(e)}"
                })
        
        # Set overall status
        results["status"] = "passed" if all(check["passed"] for check in results["checks"]) else "failed"
        
        return results
    
    def verify_redis_backup(self, backup_path: Path) -> Dict:
        """Verify Redis backup integrity"""
        results = {
            "component": "redis",
            "status": "unknown",
            "checks": []
        }
        
        # Find Redis backup file
        redis_file = backup_path / "redis.rdb"
        if not redis_file.exists():
            results["status"] = "failed"
            results["checks"].append({
                "check": "file_exists",
                "passed": False,
                "message": "Redis backup file not found"
            })
            return results
        
        # Check file size
        file_size = redis_file.stat().st_size
        if file_size == 0:
            results["checks"].append({
                "check": "file_size",
                "passed": False,
                "message": "Redis backup file is empty"
            })
        else:
            results["checks"].append({
                "check": "file_size",
                "passed": True,
                "message": f"File size: {file_size / 1024:.2f} KB"
            })
        
        # Verify RDB file format
        try:
            with open(redis_file, 'rb') as f:
                header = f.read(5)
                if header == b'REDIS':
                    results["checks"].append({
                        "check": "rdb_format",
                        "passed": True,
                        "message": "Valid Redis RDB format"
                    })
                else:
                    results["checks"].append({
                        "check": "rdb_format",
                        "passed": False,
                        "message": "Invalid Redis RDB format"
                    })
        except Exception as e:
            results["checks"].append({
                "check": "rdb_format",
                "passed": False,
                "message": f"RDB format check error: {str(e)}"
            })
        
        # Set overall status
        results["status"] = "passed" if all(check["passed"] for check in results["checks"]) else "failed"
        
        return results
    
    def verify_filesystem_backup(self, backup_path: Path) -> Dict:
        """Verify filesystem backup integrity"""
        results = {
            "component": "filesystem",
            "status": "unknown",
            "checks": []
        }
        
        fs_config = self.config["components"]["filesystem"]
        expected_paths = [Path(p).name for p in fs_config["paths"]]
        
        # Check for expected archives
        found_archives = []
        for expected in expected_paths:
            archives = list(backup_path.glob(f"{expected}.tar*"))
            if archives:
                found_archives.extend(archives)
                results["checks"].append({
                    "check": f"archive_{expected}",
                    "passed": True,
                    "message": f"Found archive for {expected}"
                })
            else:
                results["checks"].append({
                    "check": f"archive_{expected}",
                    "passed": False,
                    "message": f"Missing archive for {expected}"
                })
        
        # Verify each archive
        for archive in found_archives:
            # Check compression
            passed, message = self.verify_compressed_file(archive)
            results["checks"].append({
                "check": f"compression_{archive.name}",
                "passed": passed,
                "message": message
            })
            
            # Check encryption if applicable
            if archive.suffix == '.enc':
                passed, message = self.verify_encrypted_file(archive)
                results["checks"].append({
                    "check": f"encryption_{archive.name}",
                    "passed": passed,
                    "message": message
                })
            
            # Verify archive contents
            try:
                with tarfile.open(archive, 'r:*') as tar:
                    members = tar.getnames()
                    if len(members) > 0:
                        results["checks"].append({
                            "check": f"contents_{archive.name}",
                            "passed": True,
                            "message": f"Archive contains {len(members)} files"
                        })
                    else:
                        results["checks"].append({
                            "check": f"contents_{archive.name}",
                            "passed": False,
                            "message": "Archive is empty"
                        })
            except Exception as e:
                results["checks"].append({
                    "check": f"contents_{archive.name}",
                    "passed": False,
                    "message": f"Archive read error: {str(e)}"
                })
        
        # Set overall status
        results["status"] = "passed" if all(check["passed"] for check in results["checks"]) else "failed"
        
        return results
    
    def verify_metadata(self, backup_path: Path) -> Dict:
        """Verify backup metadata"""
        results = {
            "component": "metadata",
            "status": "unknown",
            "checks": []
        }
        
        metadata_file = backup_path / "metadata.json"
        
        # Check if metadata exists
        if not metadata_file.exists():
            results["status"] = "failed"
            results["checks"].append({
                "check": "file_exists",
                "passed": False,
                "message": "Metadata file not found"
            })
            return results
        
        # Load and validate metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check required fields
            required_fields = ["timestamp", "type", "components", "version"]
            for field in required_fields:
                if field in metadata:
                    results["checks"].append({
                        "check": f"field_{field}",
                        "passed": True,
                        "message": f"{field}: {metadata[field]}"
                    })
                else:
                    results["checks"].append({
                        "check": f"field_{field}",
                        "passed": False,
                        "message": f"Missing required field: {field}"
                    })
            
            # Validate timestamp
            try:
                datetime.fromisoformat(metadata["timestamp"])
                results["checks"].append({
                    "check": "timestamp_format",
                    "passed": True,
                    "message": "Valid timestamp format"
                })
            except:
                results["checks"].append({
                    "check": "timestamp_format",
                    "passed": False,
                    "message": "Invalid timestamp format"
                })
                
        except json.JSONDecodeError as e:
            results["checks"].append({
                "check": "json_format",
                "passed": False,
                "message": f"Invalid JSON format: {str(e)}"
            })
        except Exception as e:
            results["checks"].append({
                "check": "metadata_load",
                "passed": False,
                "message": f"Metadata load error: {str(e)}"
            })
        
        # Set overall status
        results["status"] = "passed" if all(check["passed"] for check in results["checks"]) else "failed"
        
        return results
    
    def verify_checksums(self, backup_path: Path) -> Dict:
        """Verify all file checksums"""
        results = {
            "component": "checksums",
            "status": "unknown",
            "checks": []
        }
        
        checksum_file = backup_path / "checksums.json"
        
        # Check if checksum file exists
        if not checksum_file.exists():
            results["status"] = "warning"
            results["checks"].append({
                "check": "file_exists",
                "passed": False,
                "message": "Checksum file not found (optional)"
            })
            return results
        
        # Load checksums
        try:
            with open(checksum_file, 'r') as f:
                expected_checksums = json.load(f)
            
            # Verify each file
            verified_count = 0
            failed_count = 0
            
            for file_path, expected_checksum in expected_checksums.items():
                if file_path == "checksums.json":
                    continue
                
                full_path = backup_path / file_path
                if not full_path.exists():
                    results["checks"].append({
                        "check": f"file_{file_path}",
                        "passed": False,
                        "message": f"File missing: {file_path}"
                    })
                    failed_count += 1
                    continue
                
                if self.verify_file_checksum(full_path, expected_checksum):
                    verified_count += 1
                else:
                    results["checks"].append({
                        "check": f"checksum_{file_path}",
                        "passed": False,
                        "message": f"Checksum mismatch: {file_path}"
                    })
                    failed_count += 1
            
            # Summary
            results["checks"].append({
                "check": "summary",
                "passed": failed_count == 0,
                "message": f"Verified {verified_count} files, {failed_count} failures"
            })
            
        except Exception as e:
            results["checks"].append({
                "check": "checksum_verification",
                "passed": False,
                "message": f"Checksum verification error: {str(e)}"
            })
        
        # Set overall status
        results["status"] = "passed" if all(check["passed"] for check in results["checks"] if check["check"] != "summary") else "failed"
        
        return results
    
    def verify_backup(self, backup_name: str) -> Dict:
        """Perform complete backup verification"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {
                "backup": backup_name,
                "status": "failed",
                "error": "Backup directory not found",
                "components": []
            }
        
        self.logger.info(f"Verifying backup: {backup_name}")
        
        verification_result = {
            "backup": backup_name,
            "path": str(backup_path),
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "status": "unknown",
            "components": []
        }
        
        # Verify metadata
        metadata_results = self.verify_metadata(backup_path)
        verification_result["components"].append(metadata_results)
        
        # Verify checksums
        checksum_results = self.verify_checksums(backup_path)
        verification_result["components"].append(checksum_results)
        
        # Load metadata to determine components
        metadata_file = backup_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Verify each component
            if "database" in metadata.get("components", []):
                db_results = self.verify_database_backup(backup_path)
                verification_result["components"].append(db_results)
            
            if "redis" in metadata.get("components", []):
                redis_results = self.verify_redis_backup(backup_path)
                verification_result["components"].append(redis_results)
            
            if "filesystem" in metadata.get("components", []):
                fs_results = self.verify_filesystem_backup(backup_path)
                verification_result["components"].append(fs_results)
        
        # Determine overall status
        component_statuses = [c["status"] for c in verification_result["components"]]
        if all(s == "passed" for s in component_statuses):
            verification_result["status"] = "passed"
        elif any(s == "failed" for s in component_statuses):
            verification_result["status"] = "failed"
        else:
            verification_result["status"] = "warning"
        
        # Update verification results
        self.verification_results["backups_verified"] += 1
        if verification_result["status"] == "passed":
            self.verification_results["backups_passed"] += 1
        else:
            self.verification_results["backups_failed"] += 1
            self.verification_results["issues"].append({
                "backup": backup_name,
                "status": verification_result["status"],
                "failed_components": [
                    c["component"] for c in verification_result["components"] 
                    if c["status"] == "failed"
                ]
            })
        
        return verification_result
    
    def verify_all_backups(self, limit: Optional[int] = None) -> List[Dict]:
        """Verify all available backups"""
        results = []
        
        # Get list of backups
        backups = sorted([
            d for d in self.backup_dir.iterdir() 
            if d.is_dir() and d.name.startswith("backup_")
        ], reverse=True)
        
        if limit:
            backups = backups[:limit]
        
        self.logger.info(f"Found {len(backups)} backups to verify")
        
        for backup in backups:
            result = self.verify_backup(backup.name)
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[Dict], output_file: Optional[str] = None):
        """Generate verification report"""
        report = []
        report.append("=" * 80)
        report.append("MCP Backup Verification Report")
        report.append("=" * 80)
        report.append(f"Generated: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total backups verified: {self.verification_results['backups_verified']}")
        report.append(f"Passed: {self.verification_results['backups_passed']}")
        report.append(f"Failed: {self.verification_results['backups_failed']}")
        report.append("")
        
        # Detailed results
        for result in results:
            report.append("-" * 80)
            report.append(f"Backup: {result['backup']}")
            report.append(f"Status: {result['status'].upper()}")
            report.append(f"Path: {result.get('path', 'N/A')}")
            report.append("")
            
            # Component details
            for component in result.get("components", []):
                report.append(f"  Component: {component['component']}")
                report.append(f"  Status: {component['status']}")
                
                # Show failed checks
                failed_checks = [
                    check for check in component.get("checks", [])
                    if not check["passed"]
                ]
                if failed_checks:
                    report.append("  Failed checks:")
                    for check in failed_checks:
                        report.append(f"    - {check['check']}: {check['message']}")
                
                report.append("")
        
        # Issues summary
        if self.verification_results["issues"]:
            report.append("-" * 80)
            report.append("Issues Summary:")
            for issue in self.verification_results["issues"]:
                report.append(f"  - {issue['backup']}: {', '.join(issue['failed_components'])}")
        
        report_text = "\n".join(report)
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            self.logger.info(f"Report saved to: {output_file}")
        
        return report_text

def main():
    parser = argparse.ArgumentParser(description="MCP Backup Verification")
    parser.add_argument("--backup", help="Specific backup to verify")
    parser.add_argument("--all", action="store_true", help="Verify all backups")
    parser.add_argument("--limit", type=int, help="Limit number of backups to verify")
    parser.add_argument("--config", default="config/backup_config.json",
                       help="Configuration file path")
    parser.add_argument("--report", help="Output report file path")
    parser.add_argument("--json", action="store_true", 
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    verifier = BackupVerifier(args.config)
    
    # Perform verification
    if args.backup:
        results = [verifier.verify_backup(args.backup)]
    elif args.all:
        results = verifier.verify_all_backups(args.limit)
    else:
        # Verify most recent backup
        backups = sorted([
            d.name for d in verifier.backup_dir.iterdir() 
            if d.is_dir() and d.name.startswith("backup_")
        ], reverse=True)
        
        if backups:
            results = [verifier.verify_backup(backups[0])]
        else:
            print("No backups found to verify")
            sys.exit(1)
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = verifier.generate_report(results, args.report)
        print(report)
    
    # Exit with appropriate code
    if verifier.verification_results["backups_failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()