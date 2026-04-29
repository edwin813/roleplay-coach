#!/bin/bash

# Workspace Setup Script
# Run this to initialize your 3-layer AI architecture workspace

set -e

echo "🚀 Setting up 3-Layer AI Architecture workspace..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Create virtual environment (optional but recommended)
read -p "Create virtual environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 -m venv venv
    source venv/bin/activate
    echo "✓ Virtual environment created and activated"
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Set up environment file
echo ""
if [ ! -f .env ]; then
    cp .env.template .env
    echo "✓ Created .env file from template"
    echo "⚠️  Please edit .env and add your API keys"
else
    echo "ℹ️  .env already exists, skipping"
fi

# Verify directory structure
echo ""
echo "📁 Verifying directory structure..."
for dir in directives execution .tmp; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/"
    else
        echo "  ✗ $dir/ missing!"
    fi
done

# Test example script
echo ""
echo "🧪 Testing example script..."
python3 execution/hello_world.py "World"

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Set up Google OAuth if needed (credentials.json)"
echo "3. Run: python execution/hello_world.py 'Your Name'"
echo "4. Read directives/_template.md to create your first directive"
echo ""
echo "See README.md for full documentation."
