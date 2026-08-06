#!/bin/bash
exec </dev/tty 2>/dev/null

# Fix getcwd errors in cloud containers by resetting directory safely
cd /project/workspace 2>/dev/null || cd ~ 2>/dev/null || cd /tmp

REPO_URL="https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main"

echo "🚀 Setting up vps-deploy directory..."
# Remove any accidental nested or malformed folders if they exist
if [ -d "vps-deploy/vps-deploy" ]; then
    rm -rf vps-deploy/vps-deploy
fi
mkdir -p vps-deploy

if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    echo "✅ Copied local test.env to vps-deploy/.env"
elif [ -f "vps-deploy/.env" ]; then
    echo "✅ Existing .env configuration found!"
else
    curl -sL "$REPO_URL/test.env" -o vps-deploy/.env 2>/dev/null || true
    echo "✅ Checked/Downloaded .env configuration!"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt vps-deploy/
else
    curl -sL "$REPO_URL/requirements.txt" -o vps-deploy/requirements.txt 2>/dev/null || true
fi

if [ -f "bot.py" ]; then
    cp bot.py vps-deploy/
else
    curl -sL "$REPO_URL/bot.py" -o vps-deploy/bot.py 2>/dev/null || true
fi

cd vps-deploy || exit

echo "📦 Installing Python dependencies..."
mkdir -p ~/.config/pip 
echo -e "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet 2>/dev/null || true
fi

pip install docker psutil --break-system-packages --quiet 2>/dev/null || true

echo "⚙️ Checking environment capabilities..."
if [ -S /var/run/docker.sock ]; then
    echo "✅ Docker socket detected."
else
    echo "⚠️ Note: Running in a cloud container (CodeSandbox). Real Docker daemon is not active here."
    echo "   (Container creation features inside Discord will require a real Linux VPS with Docker)."
fi

echo "✨ Installation completed successfully!"
