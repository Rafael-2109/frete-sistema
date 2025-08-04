# MCP Backup and Recovery System

A comprehensive backup and disaster recovery solution for the MCP (Model Coordination Platform) system.

## Features

- **Automated Backups**: Full and incremental backups with configurable schedules
- **Multi-Component Support**: PostgreSQL, Redis, filesystem, Docker containers
- **Cloud Storage Integration**: S3, Google Cloud Storage, Azure Blob Storage
- **Encryption**: Optional AES-256 encryption for sensitive data
- **Verification**: Automated integrity checks with checksums
- **Recovery Testing**: Disaster recovery drills in isolated environments
- **Monitoring**: Prometheus metrics and health checks
- **Notifications**: Email, Slack, and webhook alerts

## Quick Start

### 1. Configuration

Copy the template configuration:
```bash
cp templates/backup_config_template.json config/backup_config.json
```

Edit the configuration with your settings:
- Database connection details
- Redis connection
- Filesystem paths to backup
- Cloud storage credentials (optional)
- Notification settings

### 2. Generate Encryption Key

If using encryption:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Add the key to your configuration file.

### 3. Install Dependencies

```bash
pip install -r templates/requirements.backup.txt
```

### 4. Run Initial Backup

```bash
python backup_manager.py backup --type full
```

### 5. Install Cron Jobs

```bash
./backup_scheduler.sh install
```

## Usage

### Manual Backup

```bash
# Full backup
python backup_manager.py backup --type full

# Incremental backup
python backup_manager.py backup --type incremental

# List backups
python backup_manager.py list
```

### Restore Operations

```bash
# Restore from specific backup
python recovery_manager.py restore --backup backup_20240115_020000_full

# Restore specific components
python recovery_manager.py restore --backup backup_20240115_020000_full --components database redis

# Verify backup integrity
python recovery_manager.py verify --backup backup_20240115_020000_full
```

### Backup Verification

```bash
# Verify latest backup
python verify_backups.py

# Verify specific backup
python verify_backups.py --backup backup_20240115_020000_full

# Verify all backups
python verify_backups.py --all

# Generate verification report
python verify_backups.py --all --report verification_report.txt
```

### Recovery Testing

```bash
# Run disaster recovery drill
python restore_test.py --drill

# Test specific backup
python restore_test.py --test backup_20240115_020000_full

# Test latest backup
python restore_test.py --test latest
```

### Scheduler Management

```bash
# Install cron jobs
./backup_scheduler.sh install

# Uninstall cron jobs
./backup_scheduler.sh uninstall

# Run backup manually
./backup_scheduler.sh run [full|incremental]

# Verify recent backups
./backup_scheduler.sh verify

# Cleanup old backups
./backup_scheduler.sh cleanup

# Monitor backup health
./backup_scheduler.sh monitor
```

## Docker Deployment

### Using Docker Compose

```bash
# Start backup services
docker-compose -f templates/docker-compose.backup.yml up -d

# View logs
docker-compose -f templates/docker-compose.backup.yml logs -f backup_orchestrator

# Run verification
docker-compose -f templates/docker-compose.backup.yml run backup_verifier

# Run recovery drill
docker-compose -f templates/docker-compose.backup.yml run recovery_tester
```

### Building Docker Image

```bash
docker build -f templates/Dockerfile.backup -t mcp-backup:latest .
```

## Directory Structure

```
scripts/backup/
├── backup_manager.py      # Main backup orchestration
├── recovery_manager.py    # Restore operations
├── backup_scheduler.sh    # Cron job management
├── verify_backups.py      # Integrity verification
├── restore_test.py        # Recovery testing
└── templates/            # Configuration templates
    ├── backup_config_template.json
    ├── docker-compose.backup.yml
    ├── Dockerfile.backup
    ├── requirements.backup.txt
    └── crontab
```

## Backup Structure

```
/var/backups/mcp/
└── backup_20240115_020000_full/
    ├── metadata.json         # Backup metadata
    ├── checksums.json        # File checksums
    ├── database.sql.gz       # PostgreSQL dump
    ├── redis.rdb            # Redis snapshot
    ├── config.tar.gz        # Configuration files
    ├── logs.tar.gz          # Log files
    └── data.tar.gz          # Application data
```

## Configuration Options

### Retention Policy
- `retention_days`: Number of days to keep backups (default: 30)
- Old backups are automatically cleaned up

### Compression
- Supported formats: `gz`, `bz2`, `xz`
- Configurable compression level

### Encryption
- AES-256 encryption using Fernet
- Separate key management recommended

### Cloud Storage
- S3: Standard and Glacier support
- Lifecycle rules for cost optimization
- Server-side encryption

## Monitoring

### Prometheus Metrics
- Backup duration
- Backup size
- Success/failure counts
- Component-specific metrics

### Health Checks
- Last backup age
- Backup verification status
- Storage usage
- Component availability

## Notifications

### Email Alerts
- SMTP configuration
- Multiple recipients
- Customizable triggers

### Slack Integration
- Webhook-based notifications
- Channel configuration
- Rich message formatting

### Custom Webhooks
- POST requests with backup status
- Custom headers support
- JSON payload

## Best Practices

1. **Regular Testing**: Run recovery drills monthly
2. **Verification**: Enable automatic verification after backups
3. **Monitoring**: Set up alerts for backup failures
4. **Documentation**: Keep recovery procedures updated
5. **Security**: Rotate encryption keys regularly
6. **Storage**: Use lifecycle policies for cost optimization

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/backup/*.py scripts/backup/*.sh
   ```

2. **Database Connection Failed**
   - Check PostgreSQL credentials
   - Verify network connectivity
   - Ensure pg_dump is installed

3. **Insufficient Disk Space**
   - Monitor backup directory usage
   - Adjust retention policy
   - Enable cloud storage

4. **Recovery Test Failures**
   - Ensure Docker is running
   - Check container network settings
   - Verify backup integrity first

## Recovery Procedures

### Full System Recovery

1. Verify backup integrity
2. Prepare recovery environment
3. Stop production services
4. Restore database
5. Restore Redis
6. Restore filesystem
7. Restart services
8. Verify functionality

### Partial Recovery

1. Identify affected components
2. Create rollback point
3. Restore specific component
4. Verify integration
5. Monitor for issues

## Support

For issues or questions:
1. Check logs in `/app/logs/`
2. Run verification tools
3. Review configuration
4. Test in isolation first

## License

This backup system is part of the MCP project and follows the same licensing terms.