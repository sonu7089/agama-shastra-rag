#!/bin/bash

# Book RAG System - Quick Start Script
# This script helps you get started with the RAG system

echo "========================================"
echo "  Book RAG System - Quick Start"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 detected: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✓ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
GEMINI_API_KEY=your_api_key_here
PDF_PATH=path/to/your/book.pdf
OUTPUT_DIR=Output
PDF_PAGE_OFFSET=0
EOF
    echo "✓ .env template created"
    echo "⚠️  Please edit .env and add your Gemini API key"
    echo ""
else
    echo "✓ .env file exists"
    echo ""
fi

# Check if Output directory exists
if [ ! -d "Output" ]; then
    echo "📁 Output directory not found"
    echo "   Please run book_enrichment.py first to extract book data"
    echo ""
else
    # Count book folders
    book_count=$(find Output -maxdepth 1 -type d | tail -n +2 | wc -l)
    echo "✓ Output directory found with $book_count book folder(s)"
    echo ""
fi

# Check if index exists
if [ ! -d "chroma_db" ]; then
    echo "📊 Vector database not found"
    
    if [ -d "Output" ] && [ $book_count -gt 0 ]; then
        echo ""
        read -p "Would you like to index your books now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🔨 Running indexer..."
            python3 indexer.py
            echo ""
        fi
    fi
else
    echo "✓ Vector database found"
    echo ""
fi

echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. If not done, extract book data:"
echo "   python book_enrichment.py"
echo ""
echo "2. Index the extracted data:"
echo "   python indexer.py"
echo ""
echo "3. Launch the chat interface:"
echo "   streamlit run app.py"
echo ""
echo "4. Or test retrieval in CLI:"
echo "   python retriever.py"
echo ""
echo "For detailed documentation, see RAG_README.md"
echo ""
