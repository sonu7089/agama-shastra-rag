# Book RAG System Documentation

## Overview

This RAG (Retrieval-Augmented Generation) system enables intelligent querying and interaction with enriched book data. The system consists of three main components:

1. **Indexer** (`indexer.py`) - Indexes extracted book data into a vector database
2. **Retriever** (`retriever.py`) - Retrieves relevant context based on queries using a local embedding model
3. **Chat Interface** (`app.py`) - Web-based chat interface powered by Gemini AI

## Architecture

```
┌─────────────┐
│   User      │
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│   Streamlit Chat Interface      │
│         (app.py)                │
└──────┬─────────────┬────────────┘
       │             │
       │             ▼
       │    ┌────────────────────┐
       │    │  Local Embedding   │
       │    │      Model         │
       │    │ (sentence-trans.)  │
       │    └──────┬─────────────┘
       │           │
       │           ▼
       │    ┌────────────────────┐
       │    │   ChromaDB         │
       │    │  Vector Database   │
       │    └──────┬─────────────┘
       │           │
       │           ▼
       │    ┌────────────────────┐
       │    │  Retrieved Context │
       │    └──────┬─────────────┘
       │           │
       ▼           ▼
┌─────────────────────────────────┐
│    Gemini 2.5 Pro API           │
│  (Response Generation)          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────┐
│  Response   │
│  to User    │
└─────────────┘
```

## Components

### 1. Indexer (`indexer.py`)

The indexer processes all extracted book data and creates embeddings for efficient retrieval.

#### Features:
- **Multi-level Indexing**: Indexes chapters, sections, summaries, entities, and metadata
- **Smart Chunking**: Creates specialized chunks for different content types:
  - Chapter summaries
  - Section content
  - Historical figures
  - Historical events
  - Geographic locations
  - Terminology (Sanskrit/Hindi terms)
  - Quotations
  - References and notes
  - Glossary terms
- **Rich Metadata**: Stores comprehensive metadata for filtering and context
- **Local Embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` model (offline capable)
- **Persistent Storage**: Uses ChromaDB for efficient vector storage

#### Usage:

```bash
# Basic usage (indexes all books in Output folder)
python indexer.py

# Clear existing index and rebuild
python indexer.py --clear

# Custom output directory
python indexer.py --output /path/to/output

# Custom database path
python indexer.py --db /path/to/chroma_db
```

#### What Gets Indexed:

For each book folder, the indexer processes:
- `book_structure.json` - Book metadata (optional)
- `Preface.json`, `Foreword.json`, `Introduction.json` - Front matter
- `Chapter_*.json` - All chapters with sections and entities
- `Appendix_*.json` - All appendixes
- `References_and_Notes.json` - References organized by chapter
- `Glossary.json` - Terminology definitions
- `Consolidated_Metadata.json` - Aggregated metadata

#### Chunk Types:

| Chunk Type | Description | Metadata |
|------------|-------------|----------|
| `chapter_summary` | High-level chapter overview | book_name, chapter_number, chapter_title, keywords |
| `section_content` | Detailed section content | + section_number, section_title, page_range |
| `historical_figure` | People mentioned in the book | + entity_name, entity_role, entity_dates |
| `historical_event` | Events and their dates | + event_name, event_date |
| `geographic_location` | Places and locations | + location_name |
| `terminology` | Sanskrit/Hindi terms | + term, transliteration, translation |
| `quotation` | Quotes and citations | + source |
| `reference_note` | Chapter-specific references | + note_number |
| `glossary_term` | Glossary definitions | + term, transliteration |
| `appendix` | Appendix content | appendix_id, appendix_title, purpose |
| `front_matter` | Preface, foreword, etc. | section_name, page_range |

### 2. Retriever (`retriever.py`)

The retriever provides flexible query interfaces for context retrieval.

#### Features:
- **Semantic Search**: Uses embeddings for meaning-based retrieval
- **Flexible Filtering**: Filter by book, chapter, or chunk type
- **Multiple Query Modes**: Different retrieval strategies
- **Context Formatting**: Formats results for RAG prompts
- **Specialized Searches**: Dedicated methods for specific entity types

#### Usage:

```python
from retriever import BookRetriever

# Initialize
retriever = BookRetriever(db_path="chroma_db")

# Basic retrieval
results = retriever.retrieve_with_context("What is dharma?", n_results=5)

# Retrieve from specific book
results = retriever.retrieve_from_book(
    "What are the main themes?",
    book_name="YourBookName",
    n_results=5
)

# Retrieve from specific chapter
results = retriever.retrieve_from_chapter(
    "Key events?",
    book_name="YourBookName",
    chapter_number="1",
    n_results=3
)

# Search for terminology
terms = retriever.search_terminology("dharma", n_results=3)

# Search for historical figures
figures = retriever.search_historical_figures("Gandhi", n_results=3)

# Get formatted context for RAG
context = retriever.get_context_for_rag("Explain the concept...", n_results=5)

# Get available books
books = retriever.get_available_books()
```

#### Interactive CLI:

```bash
python retriever.py
```

This launches an interactive query interface for testing retrieval.

### 3. Chat Interface (`app.py`)

A Streamlit-based web interface for conversational interaction with your book data.

#### Features:
- **Chat Interface**: Natural conversation flow with history
- **Context Display**: Shows retrieved context for transparency
- **Flexible Filtering**: Filter by book or content type
- **Configurable Retrieval**: Adjust number of context chunks
- **Rich Metadata**: Displays source, chapter, and page information
- **Example Queries**: Quick-start query templates
- **Statistics Dashboard**: Shows indexing statistics

#### Usage:

```bash
# Run the Streamlit app
streamlit run app.py

# Or with custom port
streamlit run app.py --server.port 8501
```

Then open your browser to `http://localhost:8501`

#### Configuration:

In the sidebar, you can configure:
- **Gemini API Key**: Your Google Gemini API key
- **Database Path**: Path to ChromaDB (default: `chroma_db`)
- **Context Chunks**: Number of relevant chunks to retrieve (1-10)
- **Filter by Book**: Limit search to specific book
- **Filter by Type**: Focus on specific content types

#### Chat Features:

1. **Ask Questions**: Type natural language questions
2. **View Context**: See what context was retrieved for each answer
3. **Filter Results**: Use sidebar filters to narrow search
4. **Chat History**: Maintains conversation context
5. **Clear History**: Reset conversation anytime

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `chromadb` - Vector database
- `sentence-transformers` - Local embedding model
- `streamlit` - Web interface
- `torch` - PyTorch for embeddings
- `tqdm` - Progress bars
- All existing dependencies

### 2. Set Up Environment Variables

Create or update `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
PDF_PATH=path/to/your/book.pdf
OUTPUT_DIR=Output
PDF_PAGE_OFFSET=0
```

### 3. Extract Book Data (if not done)

```bash
python book_enrichment.py
```

This creates the structured JSON files in the `Output` folder.

### 4. Index the Data

```bash
python indexer.py
```

This creates the vector database in the `chroma_db` folder.

### 5. Launch the Chat Interface

```bash
streamlit run app.py
```

## Complete Workflow

```bash
# 1. Extract book data (run once per book)
python book_enrichment.py

# 2. Index the extracted data (run after extraction or when adding new books)
python indexer.py --clear

# 3. Launch the chat interface
streamlit run app.py
```

## Example Queries

### General Questions
- "What are the main themes of this book?"
- "Summarize chapter 5"
- "What is the author's main argument?"

### Specific Entities
- "Who is [Historical Figure]?"
- "What happened in [Event]?"
- "Explain the term [Sanskrit term]"
- "What is the significance of [Location]?"

### Comparative Questions
- "How does the author compare X and Y?"
- "What are the differences between chapters 2 and 3?"

### Research Questions
- "What sources does the author cite about [topic]?"
- "What controversies are mentioned?"
- "What are the key dates in the timeline?"

## Advanced Usage

### Programmatic Access

You can use the retriever programmatically in your own scripts:

```python
from retriever import BookRetriever
import google.generativeai as genai

# Initialize
retriever = BookRetriever()
genai.configure(api_key="your_api_key")
model = genai.GenerativeModel('gemini-2.5-pro')

# Get context
query = "What is dharma?"
context = retriever.get_context_for_rag(query, n_results=5)

# Generate response
prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
response = model.generate_content(prompt)

print(response.text)
```

### Batch Processing

Process multiple queries:

```python
from retriever import BookRetriever

retriever = BookRetriever()

queries = [
    "What are the main themes?",
    "Who are the key figures?",
    "What is the timeline?"
]

for query in queries:
    results = retriever.retrieve_with_context(query, n_results=3)
    print(f"\nQuery: {query}")
    for result in results:
        print(f"  - {result['text'][:100]}...")
```

### Custom Filtering

```python
# Only retrieve chapter summaries
results = retriever.retrieve_by_chunk_type(
    "main ideas",
    chunk_type="chapter_summary",
    n_results=5
)

# Only search in specific book and chapter
results = retriever.retrieve_with_context(
    "key events",
    n_results=3,
    filter_by={
        'book_name': 'MyBook',
        'chapter_number': '3'
    }
)
```

## Performance Considerations

### Embedding Model
- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Speed**: ~1000 sentences/second on CPU
- **Size**: ~80MB
- **Quality**: Good balance of speed and accuracy

### ChromaDB
- **Storage**: Persistent on disk
- **Query Speed**: Sub-second for most queries
- **Scalability**: Handles 100k+ documents efficiently

### Retrieval Speed
- **Query Embedding**: ~10-50ms
- **Vector Search**: ~10-100ms (depending on database size)
- **Total**: Usually under 200ms

### Gemini API
- **Response Time**: 1-5 seconds depending on context size
- **Cost**: Based on token usage
- **Rate Limits**: Follow Google's API limits

## Troubleshooting

### No Index Found
```
Error: Please run indexer.py first to create the index.
```
**Solution**: Run `python indexer.py` to create the index.

### No Books Found
```
No book folders found to index
```
**Solution**: Ensure the `Output` folder exists and contains book folders with JSON files.

### Embedding Model Download
The first time you run the indexer, it will download the embedding model (~80MB). This is a one-time download.

### ChromaDB Errors
If you encounter ChromaDB errors, try clearing and rebuilding:
```bash
rm -rf chroma_db
python indexer.py
```

### Streamlit Port Already in Use
```bash
streamlit run app.py --server.port 8502
```

### API Key Issues
Ensure your Gemini API key is valid and has sufficient quota.

## File Structure

```
project/
├── book_enrichment.py      # Original extraction script
├── indexer.py              # Indexing script
├── retriever.py            # Retrieval interface
├── app.py                  # Streamlit chat interface
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── Output/                 # Extracted book data
│   └── BookName/
│       ├── book_structure.json
│       ├── Chapter_*.json
│       ├── Appendix_*.json
│       ├── References_and_Notes.json
│       ├── Glossary.json
│       └── Consolidated_Metadata.json
└── chroma_db/              # Vector database (created by indexer)
    └── (database files)
```

## Best Practices

1. **Index After Each Extraction**: Run the indexer after processing new books
2. **Clear Index When Needed**: Use `--clear` flag if you've updated the extraction format
3. **Adjust Context Chunks**: Experiment with different numbers of chunks for optimal results
4. **Use Filters**: When you know the book or chapter, use filters for better precision
5. **Review Context**: Enable "Show Retrieved Context" to verify relevant information is being retrieved
6. **Refine Queries**: More specific queries usually yield better results

## Future Enhancements

Possible improvements:
- Multi-modal search (include image descriptions)
- Query expansion and reformulation
- Answer caching for common queries
- Export chat conversations
- Comparison mode for multiple books
- Timeline visualization
- Entity relationship graphs
- Citation management

## License

This RAG system is provided as-is for educational and commercial use.
