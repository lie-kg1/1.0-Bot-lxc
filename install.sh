#!/bin/bash

echo "🚀 Starting installation process..."

if [ -d "vps-deploy" ]; then
    cd vps-deploy
    echo "📁 Moved into vps-deploy directory."
fi

if [ -f "test.env" ]; then
    cp test.env .env
    echo "✅ Copied test.env to .env"
else
    echo "⚠️ test.env not found, skipping environment file copy."
fi

echo "📦 Installing python3-pip..."
apt update && apt install python3-pip -y

echo "⚙️ Configuring pip settings..."
mkdir -p ~/.config/pip 
echo -e "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

if [ -f "requirements.txt" ]; then
    echo "📥 Installing requirements..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, skipping python package installation."
fi

echo "✨ Installation completed successfully!"
