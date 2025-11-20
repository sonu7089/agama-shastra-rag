# Quick Start Guide - Ultra-Rich RAG System

## 📁 Project Structure

```
rag/
├── src/                          # All Python source code
│   ├── app.py                    # Streamlit web application
│   ├── indexer_ultrarich.py      # NEW: Ultra-rich indexer
│   ├── indexer.py                # OLD: Original indexer (kept for reference)
│   ├── retriever.py              # Retrieval engine
│   ├── reranker.py               # Cross-encoder reranking
│   ├── book_enrichment.py        # Book metadata extraction
│   ├── manual_enrich.py          # Manual chapter enrichment
│   ├── test_retrieval.py         # Test retrieval quality
│   └── test_rag_system.py        # Full system test
├── documentation/                # All markdown documentation
├── Output/                       # Enriched book JSON files
├── chroma_db/                    # Vector database (61 chunks)
└── README.md                     # Main documentation
```

## 🚀 Usage

### 1. Run the Streamlit App

```bash
cd c:\Users\PC\Downloads\AI\rag
streamlit run src/app.py
```

### 2. Re-index Books (if needed)

**Using the NEW ultra-rich indexer** (recommended):
```bash
python src/indexer_ultrarich.py --clear
```

**Using the old indexer** (creates 1000+ fragments):
```bash
python src/indexer.py --clear
```

### 3. Test Retrieval Quality

```bash
python src/test_retrieval.py
```

### 4. Enrich a Specific Chapter

```bash
python src/manual_enrich.py --chapter 2
python src/manual_enrich.py --appendix 1
```

## 📊 What Changed?

### Before (Old Indexer)
- **1002 chunks** - mostly fragments
- Retrieved: "Term: pātra - Actor"
- LLM had to synthesize from many fragments

### After (Ultra-Rich Indexer)
- **61 chunks** - self-contained with inline metadata
- Retrieved: Full section with all terms defined inline
- LLM gets complete answer in one chunk

## 🔑 Key Features

### Ultra-Rich Chunks Include:
✅ Full section content (500-1000 words)
✅ Section summary
✅ Key concepts
✅ Sanskrit terms with translations (inline)
✅ Historical figures and events (inline)
✅ Source citations

### Chunk Types:
1. **Section Content** - Full text + inline metadata
2. **Chapter Summary** - Overview + key arguments
3. **Appendix Content** - Scholarly essays (split by topic)
4. **Metadata Indexes** - Book-wide figures, timeline, terms

## 🎯 Environment Variables

Required in `.env`:
```
GEMINI_API_KEY=your_key_here
HF_TOKEN=your_huggingface_token  # For embeddinggemma-300m
```

## 📝 Notes

- The database uses `google/embeddinggemma-300m` (768-dim embeddings)
- Requires HuggingFace authentication for the embedding model
- Re-indexing takes ~2-3 minutes for 2 books
- Retrieval uses cross-encoder reranking for better relevance
