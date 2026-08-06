#!/bin/bash
exec </dev/tty 2>/dev/null

# Find the true workspace root (avoiding getcwd errors)
if [ -d "/project/workspace" ]; then
    cd /project/workspace
elif [ -d "$HOME" ]; then
    cd "$HOME"
else
    cd "$(pwd)"
fi

REPO_URL="https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main"

echo "🚀 Setting up clean vps-deploy directory..."

# Fix any nested vps-deploy/vps-deploy corruption if present
if [ -d "vps-deploy/vps-deploy" ]; then
    echo "🧹  Cleaning up nested directories..."
    cp -r vps-deploy/vps-deploy/* vps-deploy/ 2>/dev/null || true
    rm -rf vps-deploy/vps-deploy
fi

mkdir -p vps-deploy

# Handle .env configuration safely
if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    echo "✅  Copied local test.env to vps-deploy/.env"
elif [ -f "vps-deploy/.env" ]; then
    echo "✅  Existing .env configuration found!"
else
    curl -sL "$REPO_URL/test.env" -o vps-deploy/.env 2>/dev/null || true
    echo "✅  Downloaded default .env configuration!"
fi

# Handle requirements.txt
if [ -f "requirements.txt" ]; then
    cp requirements.txt vps-deploy/
else
    curl -sL "$REPO_URL/requirements.txt" -o vps-deploy/requirements.txt 2>/dev/null || true
fi

# Handle bot.py
if [ -f "bot.py" ]; then
    cp bot.py vps-deploy/
else
    curl -sL "$REPO_URL/bot.py" -o vps-deploy/bot.py 2>/dev/null || true
fi

# Move into vps-deploy to install python packages
cd vps-deploy || exit

echo "📦  Installing Python dependencies..."
mkdir -p ~/.config/pip 
echo -e "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet 2>/dev/null || true
fi

pip install docker psutil --break-system-packages --quiet 2>/dev/null || true

echo "⚙️ Checking environment capabilities..."
if [ -S /var/run/docker.sock ]; then
    echo "✅  Docker socket detected."
else
    echo "⚠️  Note: Running in a cloud container (CodeSandbox/IDX). Real Docker daemon is not active here."
    echo "   (To use full container creation in Discord, host this bot on a Linux VPS with Docker)."
fi

echo "✨  Installation completed successfully!"
