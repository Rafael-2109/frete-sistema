#!/bin/bash
# Automated deployment script for Frete Sistema

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"your-registry.com"}
IMAGE_NAME="frete-sistema"
IMAGE_TAG=${2:-$(git rev-parse --short HEAD)}
NAMESPACE="frete-sistema"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check kubectl for k8s deployment
    if [[ "$ENVIRONMENT" == "kubernetes" ]] && ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check docker-compose for local deployment
    if [[ "$ENVIRONMENT" == "local" ]] && ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi
    
    log_info "All requirements met"
}

run_tests() {
    log_info "Running tests..."
    
    # Run unit tests
    python -m pytest tests/unit -v --cov=app --cov-report=term-missing
    
    # Run integration tests if database is available
    if [[ -n "${DATABASE_URL:-}" ]]; then
        python -m pytest tests/integration -v
    fi
    
    # Run security checks
    python -m bandit -r app/ -f json -o security_report.json || true
    
    log_info "Tests completed"
}

build_docker_image() {
    log_info "Building Docker image..."
    
    # Build the image
    docker build \
        -t ${IMAGE_NAME}:${IMAGE_TAG} \
        -t ${IMAGE_NAME}:latest \
        -f deployment/docker/Dockerfile \
        .
    
    # Tag for registry
    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
    docker tag ${IMAGE_NAME}:latest ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
    
    log_info "Docker image built successfully"
}

push_docker_image() {
    log_info "Pushing Docker image to registry..."
    
    # Login to registry if credentials are provided
    if [[ -n "${DOCKER_USERNAME:-}" ]] && [[ -n "${DOCKER_PASSWORD:-}" ]]; then
        echo "${DOCKER_PASSWORD}" | docker login ${DOCKER_REGISTRY} -u ${DOCKER_USERNAME} --password-stdin
    fi
    
    # Push images
    docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
    docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
    
    log_info "Docker image pushed successfully"
}

deploy_local() {
    log_info "Deploying to local environment..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f .env ]]; then
        cp .env.example .env
        log_warn "Created .env file from .env.example. Please update with your values."
    fi
    
    # Start services
    docker-compose -f deployment/docker-compose.yml up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Run migrations
    docker-compose -f deployment/docker-compose.yml exec app flask db upgrade
    
    # Initialize permissions
    docker-compose -f deployment/docker-compose.yml exec app python scripts/initialize_permissions_render.py
    
    log_info "Local deployment completed"
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Update image in deployment
    kubectl set image deployment/frete-sistema-app \
        app=${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
        -n ${NAMESPACE}
    
    # Wait for rollout to complete
    kubectl rollout status deployment/frete-sistema-app -n ${NAMESPACE}
    
    # Run migrations as a job
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: migrate-${IMAGE_TAG}
  namespace: ${NAMESPACE}
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
        command: ["flask", "db", "upgrade"]
        envFrom:
        - configMapRef:
            name: frete-sistema-config
        - secretRef:
            name: frete-sistema-secret
EOF
    
    # Wait for migration to complete
    kubectl wait --for=condition=complete job/migrate-${IMAGE_TAG} -n ${NAMESPACE} --timeout=300s
    
    log_info "Kubernetes deployment completed"
}

deploy_render() {
    log_info "Deploying to Render.com..."
    
    # Render handles builds automatically via render.yaml
    # This function is for local validation before pushing
    
    # Validate render.yaml
    if [[ ! -f render.yaml ]]; then
        log_error "render.yaml not found"
        exit 1
    fi
    
    # Check for required environment variables in Render dashboard
    log_warn "Ensure these environment variables are set in Render dashboard:"
    echo "  - DATABASE_URL"
    echo "  - SECRET_KEY"
    echo "  - REDIS_URL (if using Redis)"
    echo "  - AWS credentials (if using S3)"
    
    # Push to git (Render auto-deploys from git)
    git add .
    git commit -m "Deploy: ${IMAGE_TAG}" || true
    git push origin main
    
    log_info "Code pushed. Render will auto-deploy from git."
}

create_backup() {
    log_info "Creating database backup..."
    
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        docker-compose -f deployment/docker-compose.yml exec postgres \
            pg_dump -U frete_user frete_sistema > backups/${BACKUP_FILE}
    elif [[ "$ENVIRONMENT" == "kubernetes" ]]; then
        kubectl exec -n ${NAMESPACE} postgres-0 -- \
            pg_dump -U frete_user frete_sistema > backups/${BACKUP_FILE}
    fi
    
    # Compress backup
    gzip backups/${BACKUP_FILE}
    
    log_info "Backup created: backups/${BACKUP_FILE}.gz"
}

rollback() {
    log_info "Rolling back deployment..."
    
    if [[ "$ENVIRONMENT" == "kubernetes" ]]; then
        kubectl rollout undo deployment/frete-sistema-app -n ${NAMESPACE}
        kubectl rollout status deployment/frete-sistema-app -n ${NAMESPACE}
    else
        log_error "Rollback not implemented for $ENVIRONMENT"
        exit 1
    fi
    
    log_info "Rollback completed"
}

# Main deployment flow
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT"
    
    check_requirements
    
    case "$ENVIRONMENT" in
        "local")
            build_docker_image
            deploy_local
            ;;
        "kubernetes")
            run_tests
            build_docker_image
            push_docker_image
            create_backup
            deploy_kubernetes
            ;;
        "render")
            run_tests
            deploy_render
            ;;
        "rollback")
            rollback
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            echo "Usage: $0 [local|kubernetes|render|rollback] [tag]"
            exit 1
            ;;
    esac
    
    log_info "Deployment completed successfully!"
}

# Run main function
main