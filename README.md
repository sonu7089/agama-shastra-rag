# Book Data Enrichment Script for RAG

This script processes PDF books using Google's Gemini API to extract structured data perfect for Retrieval-Augmented Generation (RAG) applications.

## Features

- **AI-Powered Structure Detection**: Automatically identifies chapters, sections, appendixes, and references
- **Intelligent PDF Splitting**: Creates temporary PDFs for each section to reduce context size
- **Image Description**: Describes images in detail within the content
- **Comprehensive Summaries**: Generates summaries for each section and chapter
- **Structured JSON Output**: Consistent format optimized for RAG systems
- **Rate Limiting**: Built-in delays to respect API limits

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

## Integration with RAG Systems

The structured JSON output is designed to work seamlessly with RAG systems:

1. **Chunking**: Each section is already a logical chunk
2. **Metadata**: Rich metadata (chapter, section, page numbers) for filtering
3. **Summaries**: Multiple summary levels for hierarchical retrieval
4. **Keywords**: Pre-extracted keywords for better indexing

## License

This script is provided as-is for educational and commercial use.

## Support

For issues or questions, please review the code comments and adjust prompts as needed for your specific book format.
