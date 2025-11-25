#!/bin/bash

# JobHunter Setup Script for macOS/Linux

echo "🚀 Setting up JobHunter..."

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Download spaCy model for NLP
echo "Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p logs
mkdir -p config

# Copy configuration template
if [ ! -f config/settings.yaml ]; then
    echo "Copying configuration template..."
    cp config/settings.example.yaml config/settings.yaml
    echo "⚠️  Please edit config/settings.yaml with your settings"
fi

if [ ! -f .env ]; then
    echo "Copying .env template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys and credentials"
fi

# Initialize database
echo "Initializing database..."
python -c "from src.database.models import init_db; init_db()"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your email/SMS credentials"
echo "2. Edit config/settings.yaml with your preferences"
echo "3. Run: python src/main.py (single run)"
echo "4. Or run: python src/scheduler/run.py (continuous mode)"
echo ""
