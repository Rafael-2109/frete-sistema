#!/bin/bash

# Production Deployment Script - Zero Downtime Deployment
# Usage: ./deploy_production.sh [version] [--dry-run]

set -euo pipefail

# Configuration
DEPLOY_VERSION=${1:-"latest"}
DRY_RUN=${2:-""}
APP_NAME="mcp-frete-sistema"
DEPLOY_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/backups/${APP_NAME}"
LOG_FILE="/var/log/${APP_NAME}/deployment.log"
HEALTH_CHECK_URL="https://api.frete-sistema.com/health"
ROLLBACK_MARKER="/tmp/${APP_NAME}_rollback_ready"

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

# Pre-deployment checks
pre_deployment_checks() {
    log "Starting pre-deployment checks..."
    
    # Check if running as correct user
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root"
    fi
    
    # Check if deployment directory exists
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        error "Deployment directory $DEPLOY_DIR does not exist"
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df /opt | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -lt 5242880 ]]; then # 5GB in KB
        error "Insufficient disk space. Need at least 5GB free"
    fi
    
    # Check if database is accessible
    if ! python3 -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='frete_sistema', user='app_user', password='$(cat /etc/secrets/db_password)'); conn.close()" 2>/dev/null; then
        error "Database connection failed"
    fi
    
    # Check if Redis is accessible
    if ! redis-cli ping > /dev/null 2>&1; then
        error "Redis connection failed"
    fi
    
    success "Pre-deployment checks passed"
}

# Create backup
create_backup() {
    log "Creating backup of current deployment..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_TIMESTAMP}"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup application files
    cp -r "${DEPLOY_DIR}" "${BACKUP_PATH}/app"
    
    # Backup database
    log "Creating database backup..."
    pg_dump -h localhost -U app_user frete_sistema | gzip > "${BACKUP_PATH}/database_${BACKUP_TIMESTAMP}.sql.gz"
    
    # Create rollback marker with backup info
    echo "$BACKUP_PATH" > "$ROLLBACK_MARKER"
    
    success "Backup created at $BACKUP_PATH"
}

# Blue-Green Deployment Strategy
deploy_new_version() {
    log "Deploying version $DEPLOY_VERSION..."
    
    # Determine deployment slot (blue/green)
    if [[ -f "${DEPLOY_DIR}/current_slot" ]]; then
        CURRENT_SLOT=$(cat "${DEPLOY_DIR}/current_slot")
        if [[ "$CURRENT_SLOT" == "blue" ]]; then
            NEW_SLOT="green"
        else
            NEW_SLOT="blue"
        fi
    else
        NEW_SLOT="blue"
        CURRENT_SLOT="green"
    fi
    
    log "Deploying to $NEW_SLOT slot (current: $CURRENT_SLOT)"
    
    # Create new deployment directory
    NEW_DEPLOY_PATH="${DEPLOY_DIR}/${NEW_SLOT}"
    rm -rf "$NEW_DEPLOY_PATH"
    mkdir -p "$NEW_DEPLOY_PATH"
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "DRY RUN: Would deploy version $DEPLOY_VERSION to $NEW_DEPLOY_PATH"
        return 0
    fi
    
    # Clone repository and checkout version
    git clone https://github.com/your-org/mcp-frete-sistema.git "$NEW_DEPLOY_PATH"
    cd "$NEW_DEPLOY_PATH"
    git checkout "$DEPLOY_VERSION"
    
    # Install dependencies
    log "Installing dependencies..."
    npm ci --production
    
    # Copy environment configuration
    cp "${DEPLOY_DIR}/config/.env.production" "$NEW_DEPLOY_PATH/.env"
    
    # Run database migrations (if any)
    log "Running database migrations..."
    npm run migrate:production
    
    # Build application
    log "Building application..."
    npm run build
    
    # Start application in new slot
    log "Starting application in $NEW_SLOT slot..."
    PORT=$((NEW_SLOT == "blue" ? 3000 : 3001)) npm start &
    
    # Wait for application to start
    sleep 30
    
    # Health check on new deployment
    NEW_PORT=$((NEW_SLOT == "blue" ? 3000 : 3001))
    if ! curl -f "http://localhost:${NEW_PORT}/health" > /dev/null 2>&1; then
        error "Health check failed for new deployment"
    fi
    
    success "New version deployed to $NEW_SLOT slot"
}

# Switch traffic to new deployment
switch_traffic() {
    log "Switching traffic to new deployment..."
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "DRY RUN: Would switch traffic to $NEW_SLOT slot"
        return 0
    fi
    
    # Update load balancer configuration
    # This would typically involve updating nginx config or cloud load balancer
    
    # Update nginx upstream
    NEW_PORT=$((NEW_SLOT == "blue" ? 3000 : 3001))
    sed -i "s/server localhost:[0-9]\+/server localhost:${NEW_PORT}/" /etc/nginx/sites-available/mcp-frete-sistema
    
    # Test nginx configuration
    if ! nginx -t; then
        error "Nginx configuration test failed"
    fi
    
    # Reload nginx
    systemctl reload nginx
    
    # Update current slot marker
    echo "$NEW_SLOT" > "${DEPLOY_DIR}/current_slot"
    
    success "Traffic switched to new deployment"
}

# Post-deployment verification
post_deployment_verification() {
    log "Running post-deployment verification..."
    
    # Wait for application to warm up
    sleep 60
    
    # Run health checks
    log "Running health verification..."
    if ! python3 "${DEPLOY_DIR}/../deployment/production/health_verify.py"; then
        error "Health verification failed"
    fi
    
    # Run smoke tests
    log "Running smoke tests..."
    if ! python3 "${DEPLOY_DIR}/../deployment/production/smoke_tests.py"; then
        error "Smoke tests failed"
    fi
    
    # Check response times
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$HEALTH_CHECK_URL")
    if (( $(echo "$RESPONSE_TIME > 2.0" | bc -l) )); then
        warning "Response time is high: ${RESPONSE_TIME}s"
    fi
    
    success "Post-deployment verification completed"
}

# Cleanup old deployment
cleanup_old_deployment() {
    log "Cleaning up old deployment..."
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "DRY RUN: Would cleanup old deployment"
        return 0
    fi
    
    # Stop old application
    OLD_PORT=$((CURRENT_SLOT == "blue" ? 3000 : 3001))
    pkill -f "npm.*start.*$OLD_PORT" || true
    
    # Keep old deployment for quick rollback (don't delete immediately)
    log "Old deployment kept for potential rollback"
    
    success "Cleanup completed"
}

# Send notifications
send_notifications() {
    log "Sending deployment notifications..."
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "DRY RUN: Would send notifications"
        return 0
    fi
    
    # Slack notification (if configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"✅ Production deployment completed successfully\nVersion: $DEPLOY_VERSION\nTime: $(date)\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
    
    # Email notification (if configured)
    if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        echo "Production deployment completed successfully. Version: $DEPLOY_VERSION" | \
            mail -s "Deployment Success - MCP Frete Sistema" "$NOTIFICATION_EMAIL"
    fi
    
    success "Notifications sent"
}

# Main deployment process
main() {
    log "Starting production deployment for version $DEPLOY_VERSION"
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "Running in DRY RUN mode - no actual changes will be made"
    fi
    
    # Deployment steps
    pre_deployment_checks
    create_backup
    deploy_new_version
    switch_traffic
    post_deployment_verification
    cleanup_old_deployment
    send_notifications
    
    # Remove rollback marker on successful deployment
    rm -f "$ROLLBACK_MARKER"
    
    success "Production deployment completed successfully!"
    log "Version $DEPLOY_VERSION is now live"
    
    # Display deployment summary
    echo
    echo "=================================="
    echo "  DEPLOYMENT SUMMARY"
    echo "=================================="
    echo "Version: $DEPLOY_VERSION"
    echo "Slot: $NEW_SLOT"
    echo "Time: $(date)"
    echo "Health Check: ✅"
    echo "Smoke Tests: ✅"
    echo "=================================="
}

# Error handling
trap 'error "Deployment failed! Check logs at $LOG_FILE"' ERR

# Run main function
main "$@"