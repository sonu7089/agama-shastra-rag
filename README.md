# Book Data Enrichment & RAG System

A complete pipeline for extracting structured data from PDF books and building an intelligent RAG (Retrieval-Augmented Generation) system for querying book content.

## 🚀 Quick Start

```bash
# 1. Run the quick start script
./quickstart.sh

# 2. Extract book data
python book_enrichment.py

# 3. Index the data
python indexer.py

# 4. Launch chat interface
streamlit run app.py
```

## 📦 System Components

### 1. Book Data Enrichment (`book_enrichment.py`)
Extracts structured data from PDF books using Google's Gemini API.

### 2. Vector Indexer (`indexer.py`)
Indexes extracted data into a vector database for efficient retrieval.

### 3. Retrieval System (`retriever.py`)
Provides semantic search and context retrieval using local embeddings.

### 4. Chat Interface (`app.py`)
Streamlit-based web interface for conversational interaction with your books.

## ✨ Features

### Data Extraction
- **AI-Powered Structure Detection**: Automatically identifies chapters, sections, appendixes, and references
- **Intelligent PDF Splitting**: Creates temporary PDFs for each section to reduce context size
- **Image Description**: Describes images in detail within the content
- **Comprehensive Summaries**: Generates summaries for each section and chapter
- **Structured JSON Output**: Consistent format optimized for RAG systems
- **Rich Metadata Extraction**: Historical figures, events, locations, terminology, quotations

### RAG System
- **Semantic Search**: Uses local embedding models (sentence-transformers)
- **Multi-level Indexing**: Chapters, sections, entities, terminology, references
- **Flexible Filtering**: Search by book, chapter, or content type
- **Context-Aware Retrieval**: Intelligent context assembly for AI responses
- **Chat Interface**: User-friendly web interface with conversation history
- **Dual-Model Architecture**: Local embeddings + Gemini for generation

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Get your Gemini API key:
   - Visit https://makersuite.google.com/app/apikey
   - Create a new API key
   - Save it securely

## Usage

### Basic Usage

```bash
python book_enrichment.py path/to/your/book.pdf --api-key YOUR_GEMINI_API_KEY
```

### Using Environment Variable

```bash
export GEMINI_API_KEY="your-api-key-here"
python book_enrichment.py path/to/your/book.pdf
```

### Custom Output Directory

```bash
python book_enrichment.py path/to/your/book.pdf --output CustomOutput --api-key YOUR_KEY
```

## Output Structure

The script creates the following directory structure:

```
Output/
└── YourBookName/
    ├── index.json                    # Book structure overview
    ├── Chapter_1.json               # Detailed chapter 1 data
    ├── Chapter_2.json               # Detailed chapter 2 data
    ├── ...
    ├── Appendix_A.json              # Appendix A data
    ├── Appendix_B.json              # Appendix B data
    ├── references_and_notes.json    # References section
    └── temp/                        # Temporary PDFs (can be deleted)
        ├── chapter_1.pdf
        ├── chapter_2.pdf
        └── ...
```

## JSON Output Format

### index.json
```json
{
  "chapters": [
    {
      "chapter_number": "1",
      "title": "Introduction",
      "start_page": 1,
      "end_page": 25,
      "sections": [
        {
          "section_number": "1.1",
          "title": "Background",
          "start_page": 1,
          "end_page": 10
        }
      ]
    }
  ],
  "appendixes": [...],
  "references_and_notes": {...}
}
```

### Chapter_X.json
```json
{
  "chapter_number": "1",
  "chapter_title": "Introduction",
  "number_of_pages": 25,
  "sections": [
    {
      "section_number": "1.1",
      "section_title": "Background",
      "content": "Full text content... [IMAGE: Description of image and what it conveys]",
      "summary": "Section summary",
      "key_concepts": ["concept1", "concept2"],
      "page_range": "1-10"
    }
  ],
  "chapter_summary": "Overall chapter summary",
  "key_takeaways": ["takeaway1", "takeaway2"],
  "keywords": ["keyword1", "keyword2"]
}
```

### Appendix_X.json
```json
{
  "appendix_id": "A",
  "appendix_title": "Supplementary Material",
  "number_of_pages": 10,
  "content": "Full appendix content...",
  "summary": "Appendix summary",
  "purpose": "What this appendix provides",
  "key_information": ["info1", "info2"]
}
```

### references_and_notes.json
```json
{
  "section_title": "References and Notes",
  "number_of_pages": 20,
  "content": "All references text...",
  "summary": "Summary of references",
  "reference_count": 150,
  "reference_types": ["books", "journals", "websites"]
}
```

## How It Works

1. **Structure Extraction**: Uploads the full PDF to Gemini and extracts the book structure (chapters, sections, appendixes)
2. **PDF Splitting**: Creates temporary PDFs for each section to reduce context size for AI processing
3. **Individual Processing**: Processes each section separately with focused prompts
4. **Content Extraction**: Extracts text, describes images, and generates summaries
5. **JSON Output**: Saves structured data in consistent JSON format

## Important Notes

- **Image Handling**: The script processes PDFs as images (no text extraction), perfect for scanned books
- **API Costs**: Be aware of Gemini API usage costs when processing large books
- **Processing Time**: Large books may take considerable time to process
- **Rate Limiting**: Built-in 1-second delays between requests
- **Temp Files**: Temporary PDFs are created in the temp/ folder and can be deleted after processing

## Customization

You can modify the prompts in the script to:
- Extract additional fields
- Change summary styles
- Add custom analysis
- Adjust the JSON structure

Key methods to customize:
- `extract_structure()`: Modify structure extraction prompt
- `process_chapter()`: Customize chapter processing
- `process_appendix()`: Adjust appendix processing
- `process_references()`: Change reference handling

## Troubleshooting

### API Key Issues
```
ValueError: Please provide API key via --api-key or GEMINI_API_KEY environment variable
```
**Solution**: Ensure you've provided a valid Gemini API key

### File Processing Failed
```
ValueError: File processing failed
```
**Solution**: Check PDF file integrity and size limits

### JSON Parsing Errors
**Solution**: The script automatically handles markdown code blocks, but if issues persist, check the API response

## Example Workflow

```bash
# 1. Set up environment
export GEMINI_API_KEY="your-key"

# 2. Run the script
python book_enrichment.py my_book.pdf

# 3. Check output
ls -la Output/my_book/

# 4. Use in your RAG application
# Load the JSON files and feed them to your vector database
```

## 🎯 RAG System Usage

### Indexing Books

```bash
# Index all books in Output folder
python indexer.py

# Clear and rebuild index
python indexer.py --clear

# Custom paths
python indexer.py --output /path/to/output --db /path/to/chroma_db
```

### Using the Retriever (CLI)

```bash
# Interactive retrieval mode
python retriever.py

# With custom database path
python retriever.py --db /path/to/chroma_db
```

### Launching the Chat Interface

```bash
# Start Streamlit app
streamlit run app.py

# Custom port
streamlit run app.py --server.port 8502
```

Then open your browser to `http://localhost:8501`

### Programmatic Usage

```python
from retriever import BookRetriever
import google.generativeai as genai

# Initialize
retriever = BookRetriever(db_path="chroma_db")
genai.configure(api_key="your_api_key")
model = genai.GenerativeModel('gemini-2.5-pro')

# Get context and generate response
query = "What are the main themes?"
context = retriever.get_context_for_rag(query, n_results=5)

prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
response = model.generate_content(prompt)
print(response.text)
```

## 📊 Utilities

```bash
# Show book statistics
python rag_utils.py stats

# Generate book outlines
python rag_utils.py outline

# Validate book data
python rag_utils.py validate

# Get query suggestions
python rag_utils.py suggestions
```

## 📚 Documentation

For detailed RAG system documentation, see [RAG_README.md](RAG_README.md)

Topics covered:
- Architecture and design
- Indexing strategies
- Chunk types and metadata
- Retrieval methods
- Advanced usage
- Performance optimization
- Troubleshooting

## 🏗️ System Architecture

```
PDF Book
   ↓
book_enrichment.py (Gemini API)
   ↓
Structured JSON Files
   ↓
indexer.py (Local Embeddings)
   ↓
Vector Database (ChromaDB)
   ↓
retriever.py (Semantic Search)
   ↓
app.py (Chat Interface)
   ↓
Gemini API (Response Generation)
   ↓
User Response
```

## 🔧 Configuration

Create a `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
PDF_PATH=path/to/your/book.pdf
OUTPUT_DIR=Output
PDF_PAGE_OFFSET=0
```

## Integration with RAG Systems

The structured JSON output is designed to work seamlessly with RAG systems:

1. **Chunking**: Each section is already a logical chunk
2. **Metadata**: Rich metadata (chapter, section, page numbers) for filtering
3. **Summaries**: Multiple summary levels for hierarchical retrieval
4. **Keywords**: Pre-extracted keywords for better indexing
5. **Embeddings**: Local model for fast, offline retrieval
6. **Context Assembly**: Intelligent context formatting for LLMs

## 🎨 Example Queries

- "What are the main themes of this book?"
- "Who is [historical figure]?"
- "Explain the term [Sanskrit/Hindi term]"
- "What happened in chapter 5?"
- "Summarize the main arguments"
- "What are the key dates in the timeline?"
- "What sources does the author cite about [topic]?"

## License

This project is provided as-is for educational and commercial use.

## Support

For detailed documentation and troubleshooting:
- See [RAG_README.md](RAG_README.md) for RAG system details
- Review code comments for customization options
- Check issue tracker for common problems
