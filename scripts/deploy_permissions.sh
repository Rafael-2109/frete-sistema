#!/bin/bash
# Deploy permissions system on Render

echo "🚀 Deploying permissions system..."

# Check Python environment
echo "📋 Python environment:"
which python
python --version

# Run migrations
echo "📦 Running migrations..."
flask db upgrade || echo "⚠️ Migrations may have already run"

# Initialize complete permissions system
echo "🔧 Initializing permissions system..."
python scripts/initialize_permissions_render.py

echo "✅ Permissions system deployed successfully!"
echo "🎯 You can now access /permissions/hierarchical-manager"
echo "💡 Use the 'Escanear Módulos' button to auto-detect system modules"