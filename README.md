# Agama Shastra RAG

Agama Shastra RAG is a Python project for turning long-form Agama and temple studies PDFs into structured JSON, indexing that corpus in ChromaDB, and querying it through a retrieval-augmented chat interface powered by Gemini.

## Project Status

This repository is usable, but it is still a work in progress.

- The enrichment, indexing, retrieval, and Streamlit chat flows are present.
- The repository already includes extracted JSON outputs and a prebuilt ChromaDB snapshot under `data/`.
- A static web frontend exists in `src/web/frontend/`, but the API backend it expects is not implemented in this repository.
- The included `tests/test_retrieval.py` is a manual retrieval inspection script, not an automated unit test suite.

Assumption:
The checked-in `data/outputs/Output/` and `data/chroma_db/` directories are intended to be sample or working corpus artifacts for local experimentation.

## Key Features

- PDF-to-JSON enrichment pipeline using Gemini for structure extraction and content analysis
- Structured outputs for front matter, chapters, appendixes, glossary, bibliography, references, and index sections
- Two indexing strategies:
  - standard chunking in `src/scripts/indexer.py`
  - richer semantic chunking in `src/scripts/indexer_ultrarich.py`
- ChromaDB-backed semantic retrieval with `SentenceTransformer` embeddings
- Optional cross-encoder reranking for more precise retrieval
- Streamlit chat UI with query optimization, conversation-aware retrieval, and citation-oriented prompting
- Utility scripts for corpus validation, outlines, and query suggestions

## Tech Stack

- Python 3.11+
- Google Gemini API via `google-generativeai`
- ChromaDB
- Sentence Transformers
- PyTorch
- Streamlit
- PyPDF2
- `python-dotenv`

## Repository Structure

```text
agama-shastra-rag/
├── assets/                    # Chat avatar assets
├── data/
│   ├── chroma_db/             # Prebuilt ChromaDB snapshot
│   └── outputs/Output/        # Extracted structured book JSON
├── src/
│   ├── core/                  # Retrieval, reranking, utility logic
│   ├── scripts/               # Enrichment and indexing entrypoints
│   └── web/                   # Streamlit app, prompts, experimental frontend
├── tests/                     # Manual retrieval inspection script
├── .env.example
├── requirements.txt
└── README.md
```

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## Configuration

Set these values in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
HF_TOKEN=your_huggingface_token
PDF_PATH=path/to/book.pdf
OUTPUT_DIR=data/outputs/Output
PDF_PAGE_OFFSET=0
DB_PATH=data/chroma_db
```

Notes:

- `GEMINI_API_KEY` is required for enrichment and chat generation.
- `HF_TOKEN` is required because the repository uses the gated `google/embeddinggemma-300m` model.
- `PDF_PATH` is required only when you run the enrichment pipeline on a new PDF.
- `DB_PATH` is optional in code today, but documenting it makes local setup clearer.

## Local Setup

### 1. Use the included indexed corpus

If you only want to explore the existing dataset, set:

```env
GEMINI_API_KEY=your_gemini_api_key
HF_TOKEN=your_huggingface_token
```

Then launch the chat app:

```bash
streamlit run src/web/app.py
```

### 2. Process a new PDF

Set `PDF_PATH` in `.env`, then run:

```bash
python -m src.scripts.book_enrichment
```

This generates structured JSON under `data/outputs/Output/<book-name>/`.

### 3. Build or rebuild the vector index

Standard indexing:

```bash
python -m src.scripts.indexer
```

Rebuild from scratch:

```bash
python -m src.scripts.indexer --clear
```

Ultra-rich indexing:

```bash
python -m src.scripts.indexer_ultrarich --clear
```

## Usage

### Streamlit chat app

```bash
streamlit run src/web/app.py
```

Default behavior:

- reads `GEMINI_API_KEY` from `.env`
- connects to `data/chroma_db`
- loads available books from the Chroma collection
- retrieves relevant chunks and asks Gemini to generate a grounded response

### Retrieval CLI

```bash
python -m src.core.retriever --db data/chroma_db
```

### Utility commands

```bash
python -m src.core.rag_utils stats
python -m src.core.rag_utils outline
python -m src.core.rag_utils validate
python -m src.core.rag_utils suggestions
```

### Manual enrichment for a single section

```bash
python -m src.scripts.manual_enrich --chapter 2
python -m src.scripts.manual_enrich --appendix 1
python -m src.scripts.manual_enrich --section introduction
```

## Data Flow

```text
PDF
  -> Gemini-based enrichment
  -> structured JSON files
  -> embedding generation
  -> ChromaDB collection
  -> retriever / reranker
  -> Streamlit chat response
```

## Deployment

No production deployment configuration is included yet.

Current practical deployment options:

- run the Streamlit app locally for demos
- deploy the Streamlit app manually on a VM or Streamlit Community Cloud after provisioning secrets
- add a proper API backend if you want to use the static frontend in `src/web/frontend/`

Important limitation:
`src/web/frontend/script.js` points to a backend `/chat` API, but that backend is not present in this repository today.

## Roadmap

- Add an actual automated test suite instead of manual inspection scripts
- Expose retrieval and chat through a documented API layer
- Add reproducible evaluation for retrieval quality and citation quality
- Add dataset provenance and corpus preparation notes
- Improve packaging with a `pyproject.toml` and pinned dependency strategy
- Add CI for linting, tests, and documentation checks

## Contributing

Contributions are welcome, especially around:

- retrieval quality improvements
- prompt design and grounding behavior
- packaging and developer experience
- tests, CI, and documentation

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Code of Conduct

This project follows the guidelines in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

If you discover a vulnerability, please follow [SECURITY.md](SECURITY.md).

## License

This repository currently does not grant an open-source license. See [LICENSE](LICENSE) for the current status before reusing the code or bundled data.
