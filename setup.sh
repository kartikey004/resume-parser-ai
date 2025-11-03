#!/bin/bash
# Setup script for Interview Assistant

echo "=================================="
echo "Resume Parser Example Script - Setup Script"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo ""
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install dev dependencies (optional)
echo ""
read -p "Install development dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -r requirements-dev.txt
    echo "✓ Development dependencies installed"
fi

# Setup .env file
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OPENAI_API_KEY"
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to do it later): " api_key
    if [ ! -z "$api_key" ]; then
        sed -i.bak "s/your_openai_api_key_here/$api_key/" .env
        rm .env.bak
        echo "✓ API key added to .env"
    fi
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p examples
mkdir -p tests
mkdir -p docs
echo "✓ Directories created"

# Run tests
echo ""
read -p "Run basic tests? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running tests..."
    pytest tests/test_basic.py -v
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Make sure your OPENAI_API_KEY is set in .env"
echo ""
echo "3. Try the examples:"
echo "   python examples/usage_example.py"
echo ""
echo "4. Start the API server:"
echo "   python run_api.py"
echo ""
echo "5. Or use the CLI:"
echo "   python cli.py --help"
echo ""
echo "For more information, see README.md and docs/"
echo "=================================="