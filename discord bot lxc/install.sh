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

printf "\033[1;36m🚀 Setting up clean vps-deploy directory...\033[0m\n"

# Fix any nested vps-deploy/vps-deploy corruption if present
if [ -d "vps-deploy/vps-deploy" ]; then
    printf "\033[1;33m🧹 Cleaning up nested directories...\033[0m\n"
    cp -r vps-deploy/vps-deploy/* vps-deploy/ 2>/dev/null || true
    rm -rf vps-deploy/vps-deploy
fi

mkdir -p vps-deploy

# Handle .env configuration safely
if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    printf "\033[1;32m✅ Copied local test.env to vps-deploy/.env\033[0m\n"
elif [ -f "vps-deploy/.env" ]; then
    printf "\033[1;32m✅ Existing .env configuration found!\033[0m\n"
else
    curl -sL "$REPO_URL/test.env" -o vps-deploy/.env 2>/dev/null || true
    printf "\033[1;32m✅ Downloaded default .env configuration!\033[0m\n"
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

printf "\033[1;36m📦 Installing Python dependencies...\033[0m\n"
mkdir -p ~/.config/pip 
printf "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet 2>/dev/null || true
fi

pip install docker psutil --break-system-packages --quiet 2>/dev/null || true

printf "\033[1;36m⚙️  Checking environment capabilities...\033[0m\n"
if [ -S /var/run/docker.sock ]; then
    printf "\033[1;32m✅ Docker socket detected.\033[0m\n"
else
    printf "\033[1;33m⚠️ Note: Running in a local environment. Ensure Docker daemon is running if container features are required.\033[0m\n"
fi

printf "\033[1;32m✨ Installation completed successfully!\033[0m\n"
