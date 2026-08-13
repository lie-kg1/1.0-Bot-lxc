#!/bin/bash
set -e

printf "\033[1;36m🚀 Starting complete installation and deployment...\033[0m\n"

# Navigate to the correct directory
if [ -d "botpanel" ]; then
    cd botpanel
else
    printf "\033[1;31m✗ 'botpanel' directory not found!\033[0m\n"
    exit 1
fi

# Install Node.js dependencies
printf "\033[1;33m📦 Installing dependencies...\033[0m\n"
npm install

# Setup environment variables if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    printf "\033[1;32m✅ Created .env configuration file\033[0m\n"
fi

# Run the panel application 24/7
printf "\033[1;32m✨ Launching server.js...\033[0m\n"
node server.js
