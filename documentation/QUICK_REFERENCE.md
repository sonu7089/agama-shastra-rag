# Quick Reference Guide

## 🚀 Quick Start Commands

```bash
# Setup (first time only)
./quickstart.sh

# Extract book data (first time or new books)
python book_enrichment.py

# Index the data (after extraction or updates)
python indexer.py

# Launch chat interface
streamlit run app.py

# Test system
python test_rag_system.py
```

## 📁 File Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| `book_enrichment.py` | Extract data from PDFs | New book |
| `indexer.py` | Create vector index | After extraction |
| `retriever.py` | Test retrieval | Testing/debugging |
| `app.py` | Chat interface | Daily use |
| `rag_utils.py` | Utilities | Statistics/validation |
| `test_rag_system.py` | System tests | Troubleshooting |

## 🎯 Common Tasks

### Adding a New Book
```bash
# 1. Place PDF in accessible location
# 2. Update .env with PDF_PATH
# 3. Extract
python book_enrichment.py

# 4. Index
python indexer.py

# 5. Query
streamlit run app.py
```

### Rebuilding Index
```bash
python indexer.py --clear
```

### Checking Statistics
```bash
python rag_utils.py stats
```

### Validating Data
```bash
python rag_utils.py validate
```

### Getting Query Suggestions
```bash
python rag_utils.py suggestions
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
GEMINI_API_KEY=your_api_key_here    # Required
PDF_PATH=path/to/book.pdf           # Required for extraction
OUTPUT_DIR=Output                    # Optional (default: Output)
PDF_PAGE_OFFSET=0                    # Optional (default: 0)
```

### Indexer Options
```bash
python indexer.py --clear              # Clear and rebuild
python indexer.py --output /path       # Custom output dir
python indexer.py --db /path           # Custom DB path
```

### Retriever Options
```bash
python retriever.py                    # Interactive mode
python retriever.py --db /path         # Custom DB path
```

### Streamlit Options
```bash
streamlit run app.py                   # Default (port 8501)
streamlit run app.py --server.port 8502  # Custom port
```

## 💡 Query Examples

### General Questions
- "What are the main themes of this book?"
- "Summarize the key arguments"
- "What is the author's perspective on [topic]?"

### Chapter-Specific
- "Summarize chapter 3"
- "What are the key points in chapter 5?"
- "Compare chapters 2 and 4"

### Entity Queries
- "Who is [historical figure]?"
- "Tell me about [place]"
- "What happened in [year/event]?"

### Term Definitions
- "What does [term] mean?"
- "Explain [Sanskrit term]"
- "Define [concept]"

### Reference Queries
- "What sources does the author cite about [topic]?"
- "Show me references for chapter [X]"

## 🐛 Troubleshooting

### Problem: "No module named 'chromadb'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Problem: "Index not found"
**Solution:**
```bash
python indexer.py
```

### Problem: "No books found"
**Solution:**
```bash
# Extract data first
python book_enrichment.py
```

### Problem: "API key not configured"
**Solution:**
```bash
# Create .env file
cp .env.example .env
# Edit and add your API key
nano .env
```

### Problem: "Streamlit port in use"
**Solution:**
```bash
streamlit run app.py --server.port 8502
```

## 📊 Performance Tips

1. **Optimal Context Chunks**: 3-7 chunks usually best
2. **Use Filters**: Narrow search when you know the book/chapter
3. **Specific Queries**: More specific = better results
4. **Index Once**: Don't rebuild unless data changes
5. **Clear Cache**: Restart Streamlit if UI acts weird

## 🔍 Chunk Types

| Type | Use For |
|------|---------|
| `chapter_summary` | Overview questions |
| `section_content` | Detailed information |
| `historical_figure` | People queries |
| `historical_event` | Event queries |
| `geographic_location` | Place queries |
| `terminology` | Term definitions |
| `quotation` | Finding quotes |
| `reference_note` | Citation lookup |
| `glossary_term` | Dictionary lookup |

## 📚 Documentation Index

| Document | Content |
|----------|---------|
| [README.md](README.md) | Main documentation |
| [RAG_README.md](RAG_README.md) | Detailed RAG guide |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Project summary |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Implementation details |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | This file |

## 🎨 UI Shortcuts

### In Chat Interface:
- **Clear History**: Click button in sidebar
- **Toggle Context**: Check/uncheck "Show Retrieved Context"
- **Filter by Book**: Select from dropdown
- **Filter by Type**: Select content type
- **Adjust Chunks**: Use slider (1-10)

## 🔑 Key Concepts

**RAG**: Retrieval-Augmented Generation - AI that uses retrieved context

**Embedding**: Vector representation of text for semantic search

**Chunk**: A unit of indexed text (section, entity, etc.)

**Context**: Retrieved information used to answer queries

**Metadata**: Additional info about chunks (book, chapter, type, etc.)

**Vector DB**: Database optimized for similarity search

**Semantic Search**: Search by meaning, not keywords

## 📈 System Metrics

| Metric | Value |
|--------|-------|
| Indexing Speed | ~100 chunks/sec |
| Retrieval Time | <200ms |
| Response Time | 1-5 seconds |
| Storage per Book | 1-5MB |
| Embedding Dimensions | 384 |

## 🎯 Best Practices

1. **Extract Once**: Run book_enrichment.py once per book
2. **Index After Changes**: Re-index if JSON files change
3. **Use Filters**: Narrow search scope when possible
4. **Be Specific**: Detailed queries get better results
5. **Check Context**: View retrieved context to verify relevance
6. **Adjust Chunks**: Increase if not enough info, decrease if too much
7. **Save Conversations**: Copy important responses (no auto-save yet)

## 🚨 Important Notes

- API Key is required for extraction and chat
- First query may be slow (model loading)
- Large books take time to extract (~1-2 min/chapter)
- Index is persistent - no need to rebuild unless data changes
- Local embeddings = offline retrieval after setup
- Gemini calls require internet

## 💰 Cost Considerations

| Operation | Cost |
|-----------|------|
| Indexing | $0 (local) |
| Retrieval | $0 (local) |
| Extraction | ~$0.01-0.10/chapter (Gemini) |
| Querying | ~$0.001-0.01/query (Gemini) |

## 🎓 Learning Path

1. **Start Here**: README.md → Quick Start
2. **Understand System**: PROJECT_OVERVIEW.md
3. **Deep Dive**: RAG_README.md
4. **Architecture**: ARCHITECTURE.md
5. **Customization**: Code comments in each .py file

## 🔗 Quick Links

- Get API Key: https://makersuite.google.com/app/apikey
- sentence-transformers: https://www.sbert.net/
- ChromaDB: https://www.trychroma.com/
- Streamlit: https://streamlit.io/

---

**Need More Help?**
- Run: `python test_rag_system.py`
- Check: [RAG_README.md](RAG_README.md) Troubleshooting section
- Review: Error messages and logs
