#!/bin/bash
#
# MCP Backup Scheduler - Automated backup scheduling with cron
# Handles full and incremental backups with notifications and monitoring
#

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
BACKUP_CONFIG="${PROJECT_ROOT}/config/backup_config.json"
LOG_DIR="${PROJECT_ROOT}/logs/backup"
LOCK_FILE="/var/run/mcp_backup.lock"
EMAIL_RECIPIENT="admin@example.com"
SLACK_WEBHOOK_URL=""  # Set this to enable Slack notifications

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/scheduler.log"
}

# Send notification
send_notification() {
    local subject="$1"
    local message="$2"
    local status="$3"  # success, warning, error
    
    # Email notification
    if command -v mail &> /dev/null && [ -n "$EMAIL_RECIPIENT" ]; then
        echo "$message" | mail -s "$subject" "$EMAIL_RECIPIENT"
    fi
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color="good"
        [ "$status" = "warning" ] && color="warning"
        [ "$status" = "error" ] && color="danger"
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"$subject\",
                    \"text\": \"$message\",
                    \"footer\": \"MCP Backup System\",
                    \"ts\": $(date +%s)
                }]
            }" \
            "$SLACK_WEBHOOK_URL" &> /dev/null
    fi
}

# Check if another backup is running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log "ERROR: Another backup process is already running (PID: $pid)"
            exit 1
        else
            log "WARNING: Stale lock file found, removing it"
            rm -f "$LOCK_FILE"
        fi
    fi
}

# Create lock file
create_lock() {
    echo $$ > "$LOCK_FILE"
}

# Remove lock file
remove_lock() {
    rm -f "$LOCK_FILE"
}

# Cleanup on exit
cleanup() {
    remove_lock
}
trap cleanup EXIT

# Get backup type based on day of week
get_backup_type() {
    local day_of_week=$(date +%w)
    
    # Sunday = 0, perform full backup
    if [ "$day_of_week" -eq 0 ]; then
        echo "full"
    else
        echo "incremental"
    fi
}

# Check system resources
check_system_resources() {
    local min_disk_space_gb=10
    local min_memory_gb=2
    
    # Check disk space
    local available_space=$(df -BG /var/backups | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt "$min_disk_space_gb" ]; then
        log "ERROR: Insufficient disk space (${available_space}GB available, ${min_disk_space_gb}GB required)"
        send_notification "MCP Backup Failed - Disk Space" \
            "Insufficient disk space: ${available_space}GB available, ${min_disk_space_gb}GB required" \
            "error"
        exit 1
    fi
    
    # Check memory
    local available_memory=$(free -g | awk '/^Mem:/ {print $7}')
    if [ "$available_memory" -lt "$min_memory_gb" ]; then
        log "WARNING: Low memory (${available_memory}GB available)"
    fi
}

# Pre-backup checks
pre_backup_checks() {
    log "Performing pre-backup checks..."
    
    # Check if backup manager exists
    if [ ! -f "$SCRIPT_DIR/backup_manager.py" ]; then
        log "ERROR: backup_manager.py not found"
        exit 1
    fi
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log "ERROR: Python 3 is not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import psycopg2, redis, boto3, cryptography" 2>/dev/null
    if [ $? -ne 0 ]; then
        log "ERROR: Required Python packages are not installed"
        exit 1
    fi
    
    # Check database connectivity
    if ! python3 -c "
import psycopg2
import json
with open('$BACKUP_CONFIG') as f:
    config = json.load(f)
db_config = config['components']['database']['connection']
conn = psycopg2.connect(**db_config)
conn.close()
" 2>/dev/null; then
        log "ERROR: Cannot connect to database"
        exit 1
    fi
    
    log "Pre-backup checks completed successfully"
}

# Perform backup
perform_backup() {
    local backup_type="$1"
    
    log "Starting $backup_type backup..."
    
    local start_time=$(date +%s)
    local log_file="$LOG_DIR/backup_$(date +%Y%m%d_%H%M%S).log"
    
    # Run backup manager
    cd "$PROJECT_ROOT"
    python3 "$SCRIPT_DIR/backup_manager.py" backup --type "$backup_type" --config "$BACKUP_CONFIG" 2>&1 | tee "$log_file"
    local exit_code=${PIPESTATUS[0]}
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        log "Backup completed successfully in ${duration}s"
        
        # Get backup size
        local backup_size=$(tail -n 50 "$log_file" | grep -o "Size: [0-9.]* MB" | head -1)
        
        send_notification "MCP Backup Successful" \
            "Type: $backup_type
Duration: ${duration}s
$backup_size
Log: $log_file" \
            "success"
    else
        log "ERROR: Backup failed with exit code $exit_code"
        
        # Extract error message
        local error_msg=$(tail -n 20 "$log_file" | grep -E "ERROR|CRITICAL" | tail -1)
        
        send_notification "MCP Backup Failed" \
            "Type: $backup_type
Duration: ${duration}s
Error: $error_msg
Log: $log_file" \
            "error"
        
        exit $exit_code
    fi
}

# Verify recent backups
verify_recent_backups() {
    log "Verifying recent backups..."
    
    # Run verification for backups from last 24 hours
    python3 - << EOF
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

backup_dir = Path("${PROJECT_ROOT}/var/backups/mcp")
now = datetime.now()
cutoff = now - timedelta(hours=24)

recent_backups = []
for backup in backup_dir.iterdir():
    if backup.is_dir() and backup.name.startswith("backup_"):
        try:
            timestamp_str = backup.name.split('_')[1]
            backup_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            if backup_time >= cutoff:
                recent_backups.append(backup.name)
        except:
            pass

for backup in recent_backups:
    print(f"Verifying {backup}...")
    os.system(f"cd '$PROJECT_ROOT' && python3 '$SCRIPT_DIR/verify_backups.py' --backup {backup}")
EOF
}

# Install cron jobs
install_cron() {
    log "Installing cron jobs..."
    
    # Create cron entries
    local cron_content="# MCP Backup Schedule
# Full backup every Sunday at 2 AM
0 2 * * 0 $SCRIPT_DIR/backup_scheduler.sh run >> $LOG_DIR/cron.log 2>&1

# Incremental backup Monday-Saturday at 2 AM
0 2 * * 1-6 $SCRIPT_DIR/backup_scheduler.sh run >> $LOG_DIR/cron.log 2>&1

# Verify backups daily at 6 AM
0 6 * * * $SCRIPT_DIR/backup_scheduler.sh verify >> $LOG_DIR/cron.log 2>&1

# Cleanup old backups weekly on Sunday at 4 AM
0 4 * * 0 $SCRIPT_DIR/backup_scheduler.sh cleanup >> $LOG_DIR/cron.log 2>&1

# Monitor backup health every hour
0 * * * * $SCRIPT_DIR/backup_scheduler.sh monitor >> $LOG_DIR/cron.log 2>&1
"
    
    # Install cron jobs
    (crontab -l 2>/dev/null | grep -v "# MCP Backup Schedule" | grep -v "$SCRIPT_DIR/backup_scheduler.sh"; echo "$cron_content") | crontab -
    
    log "Cron jobs installed successfully"
}

# Remove cron jobs
uninstall_cron() {
    log "Removing cron jobs..."
    
    crontab -l 2>/dev/null | grep -v "# MCP Backup Schedule" | grep -v "$SCRIPT_DIR/backup_scheduler.sh" | crontab -
    
    log "Cron jobs removed successfully"
}

# Monitor backup health
monitor_health() {
    log "Monitoring backup health..."
    
    # Check last backup status
    python3 - << EOF
import json
from datetime import datetime, timedelta
from pathlib import Path

backup_dir = Path("${PROJECT_ROOT}/var/backups/mcp")
now = datetime.now()

# Find most recent backup
latest_backup = None
latest_time = None

for backup in backup_dir.iterdir():
    if backup.is_dir() and backup.name.startswith("backup_"):
        try:
            timestamp_str = backup.name.split('_')[1]
            backup_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            if latest_time is None or backup_time > latest_time:
                latest_backup = backup
                latest_time = backup_time
        except:
            pass

if latest_backup is None:
    print("WARNING: No backups found")
    exit(1)

# Check backup age
age = now - latest_time
if age > timedelta(hours=25):  # Allow 1 hour buffer
    print(f"WARNING: Last backup is {age.total_seconds() / 3600:.1f} hours old")
    exit(1)

# Check metadata
metadata_file = latest_backup / "metadata.json"
if metadata_file.exists():
    with open(metadata_file) as f:
        metadata = json.load(f)
    print(f"Latest backup: {latest_backup.name}")
    print(f"Type: {metadata['type']}")
    print(f"Components: {', '.join(metadata['components'])}")
    print(f"Age: {age.total_seconds() / 3600:.1f} hours")
else:
    print(f"ERROR: Metadata not found for {latest_backup.name}")
    exit(1)
EOF
    
    if [ $? -ne 0 ]; then
        send_notification "MCP Backup Health Warning" \
            "Backup health check detected issues. Please investigate." \
            "warning"
    fi
}

# Main function
main() {
    local action="${1:-run}"
    
    case "$action" in
        run)
            check_lock
            create_lock
            check_system_resources
            pre_backup_checks
            
            # Determine backup type
            backup_type=$(get_backup_type)
            [ -n "$2" ] && backup_type="$2"
            
            perform_backup "$backup_type"
            ;;
        
        verify)
            verify_recent_backups
            ;;
        
        cleanup)
            log "Running backup cleanup..."
            cd "$PROJECT_ROOT"
            python3 "$SCRIPT_DIR/backup_manager.py" cleanup --config "$BACKUP_CONFIG"
            ;;
        
        monitor)
            monitor_health
            ;;
        
        install)
            install_cron
            ;;
        
        uninstall)
            uninstall_cron
            ;;
        
        test)
            log "Running test backup..."
            check_system_resources
            pre_backup_checks
            perform_backup "full"
            ;;
        
        *)
            echo "Usage: $0 {run|verify|cleanup|monitor|install|uninstall|test} [full|incremental]"
            echo ""
            echo "Commands:"
            echo "  run [type]    - Run backup (auto-detects type if not specified)"
            echo "  verify        - Verify recent backups"
            echo "  cleanup       - Remove old backups"
            echo "  monitor       - Check backup health"
            echo "  install       - Install cron jobs"
            echo "  uninstall     - Remove cron jobs"
            echo "  test          - Run test backup"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"