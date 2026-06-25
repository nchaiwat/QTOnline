#!/bin/bash

# ===========================================================================
# QT-Online Quick Deployment & Initialization Script (v2 - Better Compatibility)
# ===========================================================================

echo "🚀 Starting QT-Online Deployment..."

# 1. Check for Docker Compose command
if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Error: Docker Compose is not installed on this system."
    echo "   Please install Docker Compose first."
    exit 1
fi

echo "✅ Using command: $DOCKER_COMPOSE"

# 2. Ensure SSL directory exists
mkdir -p ssl

# 3. Build and Start Containers
echo "🏗️  Building and Starting QT-Online containers..."
$DOCKER_COMPOSE down --remove-orphans
if ! $DOCKER_COMPOSE up -d --build; then
    echo "❌ Error: Failed to start Docker containers."
    echo "   Check if another process is using Port 80 or 443."
    exit 1
fi

echo "⏳ Waiting for Database to be ready (15s)..."
sleep 15

# 4. Initialize Database Schema
echo "🗄️  Initializing Database Schema..."
if ! docker exec qt-online-web python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Database tables created.')"; then
    echo "⚠️  Warning: Database initialization might have failed."
    echo "   Ensure the 'qt-online-web' container is running."
fi

# 5. Set Folder Permissions
echo "🔐 Setting permissions..."
chmod -R 777 uploads instance 2>/dev/null || echo "Note: Permission adjustment skipped (not root)."

echo "==========================================================================="
echo "✅ QT-Online Deployment Finished!"
echo "==========================================================================="
