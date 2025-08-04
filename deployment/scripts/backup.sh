#!/bin/bash
# Automated backup script for PostgreSQL database

# Configuration
DB_NAME="${DB_NAME:-frete_sistema}"
DB_USER="${DB_USER:-frete_user}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="/backups"
RETENTION_DAYS=30
S3_BUCKET="${S3_BUCKET_NAME}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to upload to S3
upload_to_s3() {
    if [[ -n "${S3_BUCKET}" ]] && command -v aws &> /dev/null; then
        log "Uploading backup to S3..."
        aws s3 cp "${COMPRESSED_FILE}" "s3://${S3_BUCKET}/backups/$(basename ${COMPRESSED_FILE})" \
            --region "${AWS_REGION}"
        
        if [[ $? -eq 0 ]]; then
            log "Backup uploaded to S3 successfully"
        else
            log "ERROR: Failed to upload backup to S3"
        fi
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Clean local backups
    find "${BACKUP_DIR}" -name "backup_${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    
    # Clean S3 backups if configured
    if [[ -n "${S3_BUCKET}" ]] && command -v aws &> /dev/null; then
        # List and delete old S3 backups
        CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
        aws s3api list-objects-v2 \
            --bucket "${S3_BUCKET}" \
            --prefix "backups/backup_${DB_NAME}_" \
            --query "Contents[?LastModified<='${CUTOFF_DATE}'].Key" \
            --output text | \
        while read -r key; do
            if [[ -n "${key}" ]]; then
                aws s3 rm "s3://${S3_BUCKET}/${key}"
                log "Deleted old S3 backup: ${key}"
            fi
        done
    fi
}

# Main backup process
main() {
    log "Starting backup process for database: ${DB_NAME}"
    
    # Perform the backup
    log "Creating database dump..."
    PGPASSWORD="${PGPASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --verbose \
        --no-owner \
        --no-privileges \
        --exclude-table-data='audit_log' \
        --exclude-table-data='flask_session' \
        > "${BACKUP_FILE}"
    
    if [[ $? -ne 0 ]]; then
        log "ERROR: Database backup failed"
        exit 1
    fi
    
    # Compress the backup
    log "Compressing backup..."
    gzip "${BACKUP_FILE}"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "${COMPRESSED_FILE}" | cut -f1)
    log "Backup completed. Size: ${BACKUP_SIZE}"
    
    # Upload to S3 if configured
    upload_to_s3
    
    # Clean up old backups
    cleanup_old_backups
    
    log "Backup process completed successfully"
}

# Add to crontab for scheduled execution
# 0 2 * * * /backup.sh >> /var/log/backup.log 2>&1

# Run main function
main