#!/bin/bash
# Docker entrypoint script for Frete Sistema

set -e

echo "Starting Frete Sistema application..."

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
  sleep 1
done
echo "Database is ready!"

# Wait for Redis if configured
if [[ -n "${REDIS_URL}" ]]; then
  echo "Waiting for Redis..."
  REDIS_HOST=$(echo $REDIS_URL | sed -e 's/redis:\/\/.*@\(.*\):.*/\1/')
  REDIS_PORT=$(echo $REDIS_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
  while ! nc -z ${REDIS_HOST} ${REDIS_PORT}; do
    sleep 1
  done
  echo "Redis is ready!"
fi

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Initialize permissions if needed
if [[ "${INIT_PERMISSIONS:-true}" == "true" ]]; then
  echo "Initializing permissions..."
  python scripts/initialize_permissions_render.py || true
fi

# Create default admin user if it doesn't exist
if [[ -n "${ADMIN_EMAIL}" ]] && [[ -n "${ADMIN_PASSWORD}" ]]; then
  echo "Creating admin user..."
  python scripts/setup_admin_production.py || true
fi

# Install NLP models if needed
if [[ ! -f ".nlp_models_installed" ]]; then
  echo "Installing NLP models..."
  python install_nlp_models.py || true
  touch .nlp_models_installed
fi

# Start the application
echo "Starting application server..."
exec "$@"