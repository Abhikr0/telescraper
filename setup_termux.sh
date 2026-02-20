#!/bin/bash

echo "🚀 Setting up Coomer Uploader Bot in Termux..."

# Update packages
pkg update && pkg upgrade -y

# Install Python and dependencies
pkg install python -y

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example. PLEASE EDIT IT!"
else
    echo "ℹ️ .env already exists."
fi

echo "------------------------------------------------"
echo "🎉 Setup complete!"
echo "1. Edit .env with your credentials"
echo "2. Run the bot with: python main.py"
echo "------------------------------------------------"
