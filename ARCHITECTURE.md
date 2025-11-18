# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STREAMLIT WEB INTERFACE                       │
│                        (app.py)                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Chat      │  │   Context    │  │   Filters    │         │
│  │   History    │  │   Display    │  │   & Config   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────┬───────────────────────────────┬──────────────────┘
             │                               │
             │ Query                         │ Response
             ▼                               │
┌──────────────────────────────────────────┐ │
│     RETRIEVAL SYSTEM (retriever.py)      │ │
│  ┌────────────────────────────────────┐  │ │
│  │  Local Embedding Model             │  │ │
│  │  (sentence-transformers)           │  │ │
│  │  - all-MiniLM-L6-v2                │  │ │
│  │  - 384 dimensions                  │  │ │
│  │  - CPU-optimized                   │  │ │
│  └────────────────┬───────────────────┘  │ │
│                   │                       │ │
│                   ▼                       │ │
│  ┌────────────────────────────────────┐  │ │
│  │    VECTOR DATABASE (ChromaDB)      │  │ │
│  │  - Cosine similarity search        │  │ │
│  │  - Persistent storage              │  │ │
│  │  - Metadata filtering              │  │ │
│  │  - ~100k documents                 │  │ │
│  └────────────────┬───────────────────┘  │ │
└───────────────────┼──────────────────────┘ │
                    │                        │
                    ▼                        │
         ┌──────────────────────┐            │
         │  Retrieved Context   │            │
         │  - Top 5 chunks      │            │
         │  - With metadata     │            │
         │  - Ranked by score   │            │
         └──────────┬───────────┘            │
                    │                        │
                    ▼                        │
┌──────────────────────────────────────────┐ │
│        PROMPT ASSEMBLY                   │ │
│  - System instructions                   │ │
│  - Retrieved context                     │ │
│  - User query                            │ │
│  - Conversation history                  │ │
└──────────────────┬───────────────────────┘ │
                   │                          │
                   ▼                          │
┌──────────────────────────────────────────┐ │
│      GEMINI 2.5 PRO API                  │ │
│  - Response generation                   │ │
│  - Context understanding                 │ │
│  - Multilingual support                  │ │
└──────────────────┬───────────────────────┘ │
                   │                          │
                   │ Generated Response       │
                   └──────────────────────────┘
```

## Data Flow

### 1. Extraction Phase (One-time)

```
┌─────────────┐
│  PDF Book   │
└──────┬──────┘
       │
       ▼
┌────────────────────────────────┐
│  book_enrichment.py            │
│  - Gemini 2.5 Pro API          │
│  - Structure detection         │
│  - Content extraction          │
│  - Entity recognition          │
│  - Summary generation          │
└──────┬─────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Structured JSON Files (Output/BookName/)       │
│  ├── book_structure.json                        │
│  ├── Chapter_1.json                             │
│  ├── Chapter_2.json                             │
│  ├── ...                                        │
│  ├── Appendix_A.json                            │
│  ├── References_and_Notes.json                  │
│  ├── Glossary.json                              │
│  └── Consolidated_Metadata.json                 │
└─────────────────────────────────────────────────┘
```

### 2. Indexing Phase (One-time per book)

```
┌─────────────────────────────────────────────────┐
│  JSON Files (Output/BookName/)                  │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  indexer.py                                    │
│  ┌──────────────────────────────────────────┐ │
│  │  For each JSON file:                     │ │
│  │  1. Load content                         │ │
│  │  2. Create chunks by type                │ │
│  │  3. Add rich metadata                    │ │
│  │  4. Generate embeddings (local)          │ │
│  │  5. Store in ChromaDB                    │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Chunk Types Created:                           │
│  ├── chapter_summary (overview)                 │
│  ├── section_content (detailed)                 │
│  ├── historical_figure (people)                 │
│  ├── historical_event (events)                  │
│  ├── geographic_location (places)               │
│  ├── terminology (terms)                        │
│  ├── quotation (quotes)                         │
│  ├── reference_note (refs)                      │
│  ├── glossary_term (definitions)                │
│  ├── appendix (supplementary)                   │
│  └── front_matter (preface, etc.)               │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Vector Database (chroma_db/)                   │
│  - Document embeddings (384-dim)                │
│  - Metadata (book, chapter, type, page, etc.)   │
│  - Persistent on disk                           │
└─────────────────────────────────────────────────┘
```

### 3. Query Phase (Interactive)

```
┌─────────────┐
│ User Query  │
│ "What is    │
│  dharma?"   │
└──────┬──────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Query Processing (retriever.py)               │
│  ┌──────────────────────────────────────────┐ │
│  │ 1. Encode query → embedding vector       │ │
│  │    [0.12, 0.45, 0.23, ..., 0.67]        │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Vector Search (ChromaDB)                      │
│  ┌──────────────────────────────────────────┐ │
│  │ 1. Calculate cosine similarity           │ │
│  │ 2. Apply filters (book, chapter, type)   │ │
│  │ 3. Rank by relevance                     │ │
│  │ 4. Return top N results                  │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Retrieved Context                             │
│  ┌──────────────────────────────────────────┐ │
│  │ Chunk 1: (Relevance: 0.89)               │ │
│  │ Type: terminology                        │ │
│  │ Source: Book X, Chapter 2                │ │
│  │ Text: "Dharma is a Sanskrit term..."     │ │
│  │                                          │ │
│  │ Chunk 2: (Relevance: 0.85)               │ │
│  │ Type: section_content                    │ │
│  │ Source: Book X, Chapter 5                │ │
│  │ Text: "The concept of dharma..."         │ │
│  │                                          │ │
│  │ ... (up to N chunks)                     │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Prompt Construction (app.py)                  │
│  ┌──────────────────────────────────────────┐ │
│  │ System: "You are a knowledgeable..."     │ │
│  │                                          │ │
│  │ Context:                                 │ │
│  │ [Context 1] Source: ...                  │ │
│  │ Text: ...                                │ │
│  │                                          │ │
│  │ [Context 2] Source: ...                  │ │
│  │ Text: ...                                │ │
│  │                                          │ │
│  │ Query: "What is dharma?"                 │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Gemini API (Response Generation)              │
│  ┌──────────────────────────────────────────┐ │
│  │ 1. Process prompt with context           │ │
│  │ 2. Understand query intent               │ │
│  │ 3. Generate coherent response            │ │
│  │ 4. Include source attribution            │ │
│  └──────────────────────────────────────────┘ │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  Generated Response                            │
│  "Dharma is a fundamental Sanskrit concept     │
│   meaning duty, righteousness, and natural     │
│   law. According to Chapter 2 of the book,     │
│   dharma encompasses both moral duty and...    │
│                                                │
│   The term appears in multiple contexts...     │
│   (Source: Book X, Chapters 2, 5)"             │
└──────┬─────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  User sees  │
│  Response   │
│  + Context  │
└─────────────┘
```

## Component Details

### Indexer (indexer.py)

```
┌────────────────────────────────────────┐
│          BookIndexer Class             │
├────────────────────────────────────────┤
│ Methods:                               │
│  - get_all_book_folders()              │
│  - index_book_folder()                 │
│  - index_chapter()                     │
│  - index_appendix()                    │
│  - index_references()                  │
│  - index_glossary()                    │
│  - index_front_matter()                │
│  - create_text_for_embedding()         │
│  - clear_index()                       │
│  - get_stats()                         │
├────────────────────────────────────────┤
│ Dependencies:                          │
│  - sentence_transformers               │
│  - chromadb                            │
│  - tqdm                                │
└────────────────────────────────────────┘
```

### Retriever (retriever.py)

```
┌────────────────────────────────────────┐
│         BookRetriever Class            │
├────────────────────────────────────────┤
│ Methods:                               │
│  - retrieve()                          │
│  - retrieve_with_context()             │
│  - retrieve_by_chunk_type()            │
│  - retrieve_from_book()                │
│  - retrieve_from_chapter()             │
│  - multi_query_retrieve()              │
│  - get_context_for_rag()               │
│  - search_terminology()                │
│  - search_historical_figures()         │
│  - search_events()                     │
│  - search_locations()                  │
│  - get_available_books()               │
├────────────────────────────────────────┤
│ Dependencies:                          │
│  - sentence_transformers               │
│  - chromadb                            │
└────────────────────────────────────────┘
```

### Chat Interface (app.py)

```
┌────────────────────────────────────────┐
│       Streamlit Application            │
├────────────────────────────────────────┤
│ Components:                            │
│  ┌──────────────────────────────────┐ │
│  │        Sidebar                   │ │
│  │  - API Key Input                 │ │
│  │  - DB Path Config                │ │
│  │  - Context Chunks Slider         │ │
│  │  - Book Filter                   │ │
│  │  - Type Filter                   │ │
│  │  - Clear History Button          │ │
│  └──────────────────────────────────┘ │
│  ┌──────────────────────────────────┐ │
│  │      Main Chat Area              │ │
│  │  - Message History               │ │
│  │  - User Input Box                │ │
│  │  - Context Display (expandable)  │ │
│  └──────────────────────────────────┘ │
│  ┌──────────────────────────────────┐ │
│  │     Information Panel            │ │
│  │  - Statistics                    │ │
│  │  - Tips                          │ │
│  │  - Example Queries               │ │
│  └──────────────────────────────────┘ │
├────────────────────────────────────────┤
│ Functions:                             │
│  - initialize_retriever()              │
│  - initialize_gemini()                 │
│  - generate_response_with_gemini()     │
│  - format_context_display()            │
│  - main()                              │
└────────────────────────────────────────┘
```

## Storage Architecture

### File System Layout

```
project/
├── Python Scripts
│   ├── book_enrichment.py       (Extraction)
│   ├── indexer.py               (Indexing)
│   ├── retriever.py             (Retrieval)
│   ├── app.py                   (Interface)
│   ├── rag_utils.py             (Utilities)
│   └── test_rag_system.py       (Testing)
│
├── Configuration
│   ├── .env                     (API keys)
│   ├── .env.example             (Template)
│   ├── requirements.txt         (Dependencies)
│   └── .gitignore              (Git rules)
│
├── Documentation
│   ├── README.md                (Main docs)
│   ├── RAG_README.md            (RAG details)
│   ├── PROJECT_OVERVIEW.md      (Overview)
│   ├── IMPLEMENTATION_SUMMARY.md(Summary)
│   ├── CHANGELOG.md             (Changes)
│   └── ARCHITECTURE.md          (This file)
│
├── Data (gitignored)
│   ├── Output/                  (Extracted data)
│   │   └── [BookName]/
│   │       ├── book_structure.json
│   │       ├── Chapter_*.json
│   │       ├── Appendix_*.json
│   │       ├── Glossary.json
│   │       └── ...
│   │
│   └── chroma_db/               (Vector DB)
│       ├── index files
│       ├── embeddings
│       └── metadata
│
└── Cache (gitignored)
    ├── .cache/                  (Model cache)
    └── .streamlit/              (Streamlit cache)
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Local Machine                        │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │           Application Layer                     │   │
│  │  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │  Streamlit   │  │  User Browser        │   │   │
│  │  │  (Port 8501) │◄─┤  http://localhost    │   │   │
│  │  └──────────────┘  └──────────────────────┘   │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │          Processing Layer                       │   │
│  │  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │  Indexer     │  │  Retriever           │   │   │
│  │  └──────────────┘  └──────────────────────┘   │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │           Storage Layer                         │   │
│  │  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │  ChromaDB    │  │  JSON Files          │   │   │
│  │  │  (Disk)      │  │  (Disk)              │   │   │
│  │  └──────────────┘  └──────────────────────┘   │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │            Model Layer                          │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │  sentence-transformers (CPU/GPU)         │ │   │
│  │  │  - Embedding generation                  │ │   │
│  │  │  - Local processing                      │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────┘   │
│                            │                            │
└────────────────────────────┼────────────────────────────┘
                             │ HTTPS
                             │ API Call
                             ▼
                  ┌──────────────────────┐
                  │   Google Cloud       │
                  │   Gemini API         │
                  │   (2.5 Pro)          │
                  └──────────────────────┘
```

## Security Model

```
┌─────────────────────────────────────────┐
│         Security Layers                 │
├─────────────────────────────────────────┤
│                                         │
│  API Key Management                     │
│  ├── Stored in .env (gitignored)       │
│  ├── Loaded via python-dotenv          │
│  └── Never hardcoded                   │
│                                         │
│  Data Privacy                          │
│  ├── All data stored locally           │
│  ├── Embeddings generated locally      │
│  └── Only Gemini calls go external     │
│                                         │
│  Network Security                      │
│  ├── HTTPS for Gemini API              │
│  ├── No open ports (except localhost)  │
│  └── No external database connections  │
│                                         │
└─────────────────────────────────────────┘
```

## Performance Profile

```
Operation          Time         Cost        Location
──────────────────────────────────────────────────────
Query Encoding     10-50ms      $0          Local
Vector Search      10-100ms     $0          Local
Context Assembly   <10ms        $0          Local
Gemini Generation  1-5s         ~$0.001-0.01 Cloud
──────────────────────────────────────────────────────
Total Query Time:  ~1-5 seconds
Total Query Cost:  ~$0.001-0.01 (Gemini only)
```

---

**This architecture provides:**
- ✅ Fast local retrieval
- ✅ High-quality cloud generation
- ✅ Cost-effective operation
- ✅ Privacy-preserving design
- ✅ Scalable to large document sets
- ✅ Easy to extend and customize
