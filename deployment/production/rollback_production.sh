#!/bin/bash

# Production Rollback Script - Emergency Rollback Procedures
# Usage: ./rollback_production.sh [--immediate] [--database]

set -euo pipefail

# Configuration
APP_NAME="mcp-frete-sistema"
DEPLOY_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/backups/${APP_NAME}"
LOG_FILE="/var/log/${APP_NAME}/rollback.log"
ROLLBACK_MARKER="/tmp/${APP_NAME}_rollback_ready"
IMMEDIATE_MODE=${1:-""}
ROLLBACK_DATABASE=${2:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if rollback is possible
check_rollback_availability() {
    log "Checking rollback availability..."
    
    if [[ ! -f "$ROLLBACK_MARKER" ]]; then
        error "No rollback marker found. Cannot determine previous deployment state."
    fi
    
    BACKUP_PATH=$(cat "$ROLLBACK_MARKER")
    if [[ ! -d "$BACKUP_PATH" ]]; then
        error "Backup directory not found: $BACKUP_PATH"
    fi
    
    success "Rollback backup found: $BACKUP_PATH"
}

# Confirm rollback unless immediate mode
confirm_rollback() {
    if [[ "$IMMEDIATE_MODE" != "--immediate" ]]; then
        echo
        echo -e "${RED}⚠️  PRODUCTION ROLLBACK WARNING ⚠️${NC}"
        echo "This will rollback the production application to the previous version."
        echo "Current deployment will be stopped and replaced."
        echo
        read -p "Are you sure you want to proceed? (type 'ROLLBACK' to confirm): " CONFIRMATION
        
        if [[ "$CONFIRMATION" != "ROLLBACK" ]]; then
            log "Rollback cancelled by user"
            exit 0
        fi
    else
        log "Running in immediate mode - no confirmation required"
    fi
}

# Get current deployment state
get_current_state() {
    log "Analyzing current deployment state..."
    
    if [[ -f "${DEPLOY_DIR}/current_slot" ]]; then
        CURRENT_SLOT=$(cat "${DEPLOY_DIR}/current_slot")
        if [[ "$CURRENT_SLOT" == "blue" ]]; then
            ROLLBACK_SLOT="green"
        else
            ROLLBACK_SLOT="blue"
        fi
    else
        error "Cannot determine current deployment slot"
    fi
    
    log "Current slot: $CURRENT_SLOT, Rolling back to: $ROLLBACK_SLOT"
}

# Create emergency backup of current state
create_emergency_backup() {
    log "Creating emergency backup of current state..."
    
    EMERGENCY_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    EMERGENCY_BACKUP_PATH="${BACKUP_DIR}/emergency_${EMERGENCY_TIMESTAMP}"
    
    mkdir -p "$EMERGENCY_BACKUP_PATH"
    
    # Backup current application state
    if [[ -d "${DEPLOY_DIR}/${CURRENT_SLOT}" ]]; then
        cp -r "${DEPLOY_DIR}/${CURRENT_SLOT}" "${EMERGENCY_BACKUP_PATH}/app"
    fi
    
    # Quick database snapshot
    if pg_dump -h localhost -U app_user frete_sistema > "${EMERGENCY_BACKUP_PATH}/emergency_db_${EMERGENCY_TIMESTAMP}.sql" 2>/dev/null; then
        success "Emergency database backup created"
    else
        warning "Emergency database backup failed - continuing rollback"
    fi
    
    success "Emergency backup created at $EMERGENCY_BACKUP_PATH"
}

# Switch traffic back to previous deployment
switch_traffic_back() {
    log "Switching traffic back to previous deployment..."
    
    # Check if previous deployment is still available
    ROLLBACK_PATH="${DEPLOY_DIR}/${ROLLBACK_SLOT}"
    if [[ ! -d "$ROLLBACK_PATH" ]]; then
        error "Previous deployment not found at $ROLLBACK_PATH"
    fi
    
    # Start previous deployment if not running
    ROLLBACK_PORT=$((ROLLBACK_SLOT == "blue" ? 3000 : 3001))
    if ! curl -f "http://localhost:${ROLLBACK_PORT}/health" > /dev/null 2>&1; then
        log "Starting previous deployment..."
        cd "$ROLLBACK_PATH"
        PORT=$ROLLBACK_PORT npm start &
        sleep 30
        
        # Verify it started
        if ! curl -f "http://localhost:${ROLLBACK_PORT}/health" > /dev/null 2>&1; then
            error "Failed to start previous deployment"
        fi
    fi
    
    # Update nginx configuration
    sed -i "s/server localhost:[0-9]\+/server localhost:${ROLLBACK_PORT}/" /etc/nginx/sites-available/mcp-frete-sistema
    
    # Test and reload nginx
    if ! nginx -t; then
        error "Nginx configuration test failed during rollback"
    fi
    
    systemctl reload nginx
    
    # Update current slot marker
    echo "$ROLLBACK_SLOT" > "${DEPLOY_DIR}/current_slot"
    
    success "Traffic switched back to previous deployment"
}

# Restore from backup if needed
restore_from_backup() {
    log "Restoring application from backup..."
    
    BACKUP_PATH=$(cat "$ROLLBACK_MARKER")
    
    # Stop current deployment
    CURRENT_PORT=$((CURRENT_SLOT == "blue" ? 3000 : 3001))
    pkill -f "npm.*start.*$CURRENT_PORT" || true
    
    # Restore application files
    if [[ -d "${BACKUP_PATH}/app" ]]; then
        rm -rf "${DEPLOY_DIR}/${CURRENT_SLOT}"
        cp -r "${BACKUP_PATH}/app" "${DEPLOY_DIR}/${CURRENT_SLOT}"
        success "Application files restored from backup"
    fi
}

# Database rollback
rollback_database() {
    if [[ "$ROLLBACK_DATABASE" == "--database" ]]; then
        log "Rolling back database..."
        
        BACKUP_PATH=$(cat "$ROLLBACK_MARKER")
        DB_BACKUP=$(find "$BACKUP_PATH" -name "database_*.sql.gz" | head -1)
        
        if [[ -f "$DB_BACKUP" ]]; then
            warning "Database rollback is destructive and cannot be undone!"
            
            if [[ "$IMMEDIATE_MODE" != "--immediate" ]]; then
                read -p "Proceed with database rollback? (type 'ROLLBACK_DB' to confirm): " DB_CONFIRMATION
                if [[ "$DB_CONFIRMATION" != "ROLLBACK_DB" ]]; then
                    log "Database rollback skipped"
                    return 0
                fi
            fi
            
            # Create current database backup before rollback
            ROLLBACK_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            pg_dump -h localhost -U app_user frete_sistema > "${BACKUP_DIR}/pre_rollback_${ROLLBACK_TIMESTAMP}.sql"
            
            # Drop and recreate database
            dropdb -h localhost -U postgres frete_sistema
            createdb -h localhost -U postgres frete_sistema
            
            # Restore from backup
            zcat "$DB_BACKUP" | psql -h localhost -U app_user frete_sistema
            
            success "Database rolled back successfully"
        else
            warning "No database backup found - skipping database rollback"
        fi
    else
        log "Skipping database rollback (not requested)"
    fi
}

# Health verification after rollback
verify_rollback() {
    log "Verifying rollback success..."
    
    # Wait for application to stabilize
    sleep 30
    
    # Health check
    if curl -f "https://api.frete-sistema.com/health" > /dev/null 2>&1; then
        success "Application health check passed"
    else
        error "Application health check failed after rollback"
    fi
    
    # Quick functionality test
    if python3 "${DEPLOY_DIR}/../deployment/production/smoke_tests.py" --quick; then
        success "Quick smoke tests passed"
    else
        warning "Some smoke tests failed - manual verification needed"
    fi
    
    # Check response time
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "https://api.frete-sistema.com/health")
    log "Response time: ${RESPONSE_TIME}s"
}

# Stop current deployment
stop_current_deployment() {
    log "Stopping current deployment..."
    
    CURRENT_PORT=$((CURRENT_SLOT == "blue" ? 3000 : 3001))
    pkill -f "npm.*start.*$CURRENT_PORT" || true
    
    # Wait for graceful shutdown
    sleep 10
    
    success "Current deployment stopped"
}

# Send rollback notifications
send_rollback_notifications() {
    log "Sending rollback notifications..."
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🔄 PRODUCTION ROLLBACK COMPLETED\nTime: $(date)\nPrevious slot: $ROLLBACK_SLOT\nPlease investigate and monitor closely\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
    
    # Email notification
    if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        echo "Production rollback completed. System restored to previous version. Please investigate the cause and monitor system closely." | \
            mail -s "URGENT: Production Rollback Completed - MCP Frete Sistema" "$NOTIFICATION_EMAIL"
    fi
    
    success "Rollback notifications sent"
}

# Main rollback process
main() {
    log "Starting production rollback process"
    
    echo
    echo "=================================="
    echo "  PRODUCTION ROLLBACK"
    echo "=================================="
    echo "App: $APP_NAME"
    echo "Time: $(date)"
    echo "Mode: ${IMMEDIATE_MODE:-normal}"
    echo "=================================="
    echo
    
    # Rollback steps
    check_rollback_availability
    confirm_rollback
    get_current_state
    create_emergency_backup
    
    # Choose rollback strategy
    if [[ -d "${DEPLOY_DIR}/${ROLLBACK_SLOT}" ]]; then
        # Quick rollback - switch to existing previous deployment
        log "Using quick rollback strategy (switching slots)"
        switch_traffic_back
    else
        # Full restore from backup
        log "Using full restore strategy (from backup)"
        restore_from_backup
        switch_traffic_back
    fi
    
    rollback_database
    stop_current_deployment
    verify_rollback
    send_rollback_notifications
    
    success "Production rollback completed successfully!"
    
    # Display rollback summary
    echo
    echo "=================================="
    echo "  ROLLBACK SUMMARY"
    echo "=================================="
    echo "Rollback Time: $(date)"
    echo "Active Slot: $ROLLBACK_SLOT"
    echo "Health Status: ✅"
    echo "Database: ${ROLLBACK_DATABASE:+Rolled back}"
    echo "Emergency Backup: Created"
    echo "=================================="
    echo
    echo -e "${YELLOW}IMPORTANT:${NC}"
    echo "1. Monitor system closely for next 24 hours"
    echo "2. Investigate root cause of deployment failure"
    echo "3. Emergency backup available if further issues occur"
    echo "4. Consider running full regression tests"
}

# Error handling
trap 'error "Rollback failed! Manual intervention required. Check logs at $LOG_FILE"' ERR

# Run main function
main "$@"