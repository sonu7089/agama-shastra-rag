import os
import json
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class UltraRichBookIndexer:
    """
    Ultra-Rich Book Indexer
    Creates self-contained, content-rich chunks with inline metadata
    instead of fragmenting data into tiny pieces.
    """
    
    def __init__(self, output_dir: str = "Output", db_path: str = "chroma_db"):
        self.output_dir = Path(output_dir)
        self.db_path = db_path
        
        # Initialize embedding model
        print("Loading embedding model (EmbeddingGemma-300M)...")
        self.embedding_model = SentenceTransformer('google/embeddinggemma-300m')
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="book_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"Ultra-Rich Indexer initialized. Database path: {db_path}")
    
    def clear_index(self):
        """Clear existing index"""
        try:
            self.client.delete_collection("book_embeddings")
            self.collection = self.client.get_or_create_collection(
                name="book_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            print("Index cleared successfully")
        except Exception as e:
            print(f"Error clearing index: {e}")
    
    def load_json_file(self, file_path: Path) -> Dict:
        """Load JSON file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}
    
    # ==================== HELPER FUNCTIONS ====================
    
    def extract_section_terms(self, section: Dict, chapter_data: Dict) -> List[Dict]:
        """Extract Sanskrit terms mentioned in this section's content"""
        section_text = section.get('content', '').lower()
        relevant_terms = []
        
        for term in chapter_data.get('sanskrit_hindi_terms', []):
            # Check if term appears in section content
            term_name = term.get('term', '').lower()
            if term_name and term_name in section_text:
                relevant_terms.append(term)
        
        return relevant_terms[:15]  # Limit to top 15 most relevant
    
    def extract_section_figures(self, section: Dict, chapter_data: Dict) -> List[Dict]:
        """Extract historical figures mentioned in this section"""
        section_text = section.get('content', '').lower()
        relevant_figures = []
        
        for figure in chapter_data.get('historical_figures', []):
            figure_name = figure.get('name', '').lower()
            if figure_name and figure_name in section_text:
                relevant_figures.append(figure)
        
        return relevant_figures
    
    def extract_section_events(self, section: Dict, chapter_data: Dict) -> List[Dict]:
        """Extract historical events mentioned in this section"""
        section_text = section.get('content', '').lower()
        relevant_events = []
        
        for event in chapter_data.get('historical_events', []):
            event_text = event.get('event', '').lower()
            if event_text and any(word in section_text for word in event_text.split()[:3]):
                relevant_events.append(event)
        
        return relevant_events
    
    # ==================== CHUNK CREATION FUNCTIONS ====================
    
    def create_enriched_section_chunk(self, section: Dict, chapter_data: Dict, 
                                     chapter_num: str, book_name: str) -> str:
        """Create ultra-rich section chunk with inline metadata"""
        
        chapter_title = chapter_data.get('chapter_title', 'Unknown')
        section_num = section.get('section_number', '?')
        section_title = section.get('section_title', 'Unknown')
        
        parts = [
            f"Chapter {chapter_num}: {chapter_title}",
            f"Section {section_num}: {section_title}",
            "",
            "=== FULL CONTENT ===",
            section.get('content', ''),
            ""
        ]
        
        # Add summary
        if section.get('summary'):
            parts.extend([
                "=== SUMMARY ===",
                section['summary'],
                ""
            ])
        
        # Add key concepts
        if section.get('key_concepts'):
            parts.append("=== KEY CONCEPTS ===")
            for concept in section['key_concepts']:
                parts.append(f"• {concept}")
            parts.append("")
        
        # Add inline Sanskrit terms
        section_terms = self.extract_section_terms(section, chapter_data)
        if section_terms:
            parts.append("=== SANSKRIT TERMS (in this section) ===")
            for term in section_terms:
                term_line = f"• {term.get('term', '')} ({term.get('transliteration', '')})"
                if term.get('translation'):
                    term_line += f" - \"{term['translation']}\""
                if term.get('context'):
                    term_line += f" - {term['context']}"
                parts.append(term_line)
            parts.append("")
        
        # Add inline historical context
        section_figures = self.extract_section_figures(section, chapter_data)
        section_events = self.extract_section_events(section, chapter_data)
        
        if section_figures or section_events:
            parts.append("=== HISTORICAL CONTEXT ===")
            for event in section_events:
                parts.append(f"• Event: {event.get('event', '')} ({event.get('date', 'date unknown')}) - {event.get('significance', '')}")
            for figure in section_figures:
                parts.append(f"• Figure: {figure.get('name', '')} - {figure.get('role', '')} - {figure.get('significance', '')}")
            parts.append("")
        
        # Add source
        parts.extend([
            "=== SOURCE ===",
            f"Book: {book_name}, Chapter {chapter_num}, Section {section_num}, Pages {section.get('page_range', 'N/A')}"
        ])
        
        return "\n".join(parts)
    
    def create_chapter_summary_chunk(self, chapter_data: Dict, chapter_num: str, 
                                    book_name: str) -> str:
        """Create enriched chapter summary chunk"""
        
        chapter_title = chapter_data.get('chapter_title', 'Unknown')
        
        parts = [
            f"Chapter {chapter_num}: {chapter_title} - Overview",
            "",
            "=== CHAPTER SUMMARY ===",
            chapter_data.get('chapter_summary', ''),
            ""
        ]
        
        # Add key arguments
        if chapter_data.get('key_arguments'):
            parts.append("=== KEY ARGUMENTS ===")
            for i, arg in enumerate(chapter_data['key_arguments'], 1):
                parts.append(f"{i}. {arg}")
            parts.append("")
        
        # Add key takeaways
        if chapter_data.get('key_takeaways'):
            parts.append("=== KEY TAKEAWAYS ===")
            for takeaway in chapter_data['key_takeaways']:
                parts.append(f"• {takeaway}")
            parts.append("")
        
        # Add main topics
        if chapter_data.get('sections'):
            parts.append("=== MAIN TOPICS COVERED ===")
            for section in chapter_data['sections']:
                parts.append(f"• {section.get('section_title', 'Unknown')}")
            parts.append("")
        
        # Add keywords
        if chapter_data.get('keywords'):
            parts.append("=== KEYWORDS ===")
            parts.append(", ".join(chapter_data['keywords']))
            parts.append("")
        
        # Add source
        parts.extend([
            "=== SOURCE ===",
            f"Book: {book_name}, Chapter {chapter_num} (Complete)"
        ])
        
        return "\n".join(parts)
    
    def split_long_text(self, text: str, max_words: int = 2000) -> List[str]:
        """Split long text into chunks of approximately max_words"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunks.append(" ".join(chunk_words))
        
        return chunks if chunks else [text]
    
    def create_appendix_chunk(self, content_chunk: str, appendix_data: Dict,
                             appendix_id: str, part_num: int, book_name: str) -> str:
        """Create enriched appendix chunk"""
        
        appendix_title = appendix_data.get('appendix_title', 'Unknown')
        
        parts = [
            f"Appendix {appendix_id}: {appendix_title} - Part {part_num}",
            "",
            "=== CONTENT ===",
            content_chunk,
            ""
        ]
        
        # Add purpose (only in first part)
        if part_num == 1 and appendix_data.get('purpose'):
            parts.extend([
                "=== APPENDIX PURPOSE ===",
                appendix_data['purpose'],
                ""
            ])
        
        # Add key information (only in first part)
        if part_num == 1 and appendix_data.get('key_information'):
            parts.append("=== KEY INFORMATION ===")
            for info in appendix_data['key_information'][:10]:  # First 10
                parts.append(f"• {info}")
            parts.append("")
        
        # Add source
        parts.extend([
            "=== SOURCE ===",
            f"Book: {book_name}, Appendix {appendix_id}, Part {part_num}"
        ])
        
        return "\n".join(parts)
    
    # ==================== INDEXING FUNCTIONS ====================
    
    def batch_add_chunks(self, chunks: List[Dict]):
        """Add multiple chunks to the collection in batch"""
        if not chunks:
            return
        
        ids = [chunk['id'] for chunk in chunks]
        texts = [chunk['text'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        # Generate embeddings
        print(f"  Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    def index_chapter(self, book_name: str, chapter_file: Path):
        """Index a single chapter with ultra-rich chunks"""
        chapter_data = self.load_json_file(chapter_file)
        if not chapter_data:
            return
        
        chapter_num = chapter_data.get('chapter_number', 'unknown')
        chapter_title = chapter_data.get('chapter_title', 'Unknown')
        
        print(f"    Processing Chapter {chapter_num}: {chapter_title}")
        
        chunks_to_add = []
        
        # 1. Index enriched chapter summary
        chapter_summary_text = self.create_chapter_summary_chunk(
            chapter_data, chapter_num, book_name
        )
        chunks_to_add.append({
            'id': f"{book_name}_ch{chapter_num}_summary",
            'text': chapter_summary_text,
            'metadata': {
                'book_name': book_name,
                'chapter_number': str(chapter_num),
                'chapter_title': chapter_title,
                'chunk_type': 'chapter_summary'
            }
        })
        
        # 2. Index each section with inline metadata
        for idx, section in enumerate(chapter_data.get('sections', [])):
            section_text = self.create_enriched_section_chunk(
                section, chapter_data, chapter_num, book_name
            )
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_sec{idx}",
                'text': section_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'section_number': section.get('section_number', str(idx)),
                    'section_title': section.get('section_title', ''),
                    'chunk_type': 'section_content',
                    'page_range': section.get('page_range', 'unknown')
                }
            })
        
        # 3. Batch add all chunks
        self.batch_add_chunks(chunks_to_add)
        print(f"    ✓ Added {len(chunks_to_add)} chunks for Chapter {chapter_num}")
    
    def index_appendix(self, book_name: str, appendix_file: Path):
        """Index appendix with topic-based chunks"""
        appendix_data = self.load_json_file(appendix_file)
        if not appendix_data:
            return
        
        appendix_id = appendix_data.get('appendix_id', 'unknown')
        appendix_title = appendix_data.get('appendix_title', 'Unknown')
        content = appendix_data.get('content', '')
        
        print(f"    Processing Appendix {appendix_id}: {appendix_title}")
        
        # Split large appendix content into ~2000-word chunks
        content_chunks = self.split_long_text(content, max_words=2000)
        
        chunks_to_add = []
        for idx, chunk_text in enumerate(content_chunks, 1):
            enriched_text = self.create_appendix_chunk(
                chunk_text, appendix_data, appendix_id, idx, book_name
            )
            
            chunks_to_add.append({
                'id': f"{book_name}_app{appendix_id}_part{idx}",
                'text': enriched_text,
                'metadata': {
                    'book_name': book_name,
                    'appendix_id': str(appendix_id),
                    'appendix_title': appendix_title,
                    'chunk_type': 'appendix_content',
                    'part_number': idx
                }
            })
        
        self.batch_add_chunks(chunks_to_add)
        print(f"    ✓ Added {len(chunks_to_add)} chunks for Appendix {appendix_id}")
    
    def index_consolidated_metadata(self, book_name: str, metadata_file: Path):
        """Index book-wide metadata for cross-chapter queries"""
        metadata = self.load_json_file(metadata_file)
        if not metadata:
            return
        
        print(f"    Processing Consolidated Metadata")
        
        chunks_to_add = []
        
        # Index historical figures
        if metadata.get('all_historical_figures'):
            figures = metadata['all_historical_figures']
            parts = [
                f"{book_name} - Complete Historical Figures Index",
                "",
                "=== ALL HISTORICAL FIGURES ===",
                ""
            ]
            
            for figure in figures:
                parts.append(f"{figure.get('name', 'Unknown')}")
                parts.append(f"• Role: {figure.get('role', 'N/A')}")
                parts.append(f"• Significance: {figure.get('significance', 'N/A')}")
                parts.append(f"• Dates: {figure.get('dates', 'N/A')}")
                parts.append("")
            
            parts.extend([
                "=== SOURCE ===",
                f"Book: {book_name}, Consolidated Metadata - Historical Figures"
            ])
            
            chunks_to_add.append({
                'id': f"{book_name}_figures_index",
                'text': "\n".join(parts),
                'metadata': {
                    'book_name': book_name,
                    'chunk_type': 'figures_index'
                }
            })
        
        # Index timeline
        if metadata.get('complete_timeline'):
            timeline = metadata['complete_timeline']
            parts = [
                f"{book_name} - Complete Historical Timeline",
                "",
                "=== CHRONOLOGICAL EVENTS ===",
                ""
            ]
            
            for event in timeline:
                parts.append(f"{event.get('date', 'Unknown date')}: {event.get('event', 'Unknown event')}")
                parts.append(f"  Significance: {event.get('significance', 'N/A')}")
                parts.append("")
            
            parts.extend([
                "=== SOURCE ===",
                f"Book: {book_name}, Consolidated Metadata - Timeline"
            ])
            
            chunks_to_add.append({
                'id': f"{book_name}_timeline",
                'text': "\n".join(parts),
                'metadata': {
                    'book_name': book_name,
                    'chunk_type': 'timeline'
                }
            })
        
        self.batch_add_chunks(chunks_to_add)
        print(f"    ✓ Added {len(chunks_to_add)} metadata chunks")
    
    def index_book_folder(self, book_folder: Path):
        """Index all files in a book folder with ultra-rich strategy"""
        book_name = book_folder.name
        print(f"\n📚 Indexing book: {book_name}")
        print("=" * 60)
        
        total_chunks = 0
        
        # 1. Index chapters
        chapter_files = sorted(book_folder.glob("Chapter_*.json"))
        if chapter_files:
            print(f"\n  📖 Indexing {len(chapter_files)} chapters...")
            for chapter_file in chapter_files:
                self.index_chapter(book_name, chapter_file)
        
        # 2. Index appendixes
        appendix_files = sorted(book_folder.glob("Appendix_*.json"))
        if appendix_files:
            print(f"\n  📄 Indexing {len(appendix_files)} appendixes...")
            for appendix_file in appendix_files:
                self.index_appendix(book_name, appendix_file)
        
        # 3. Index consolidated metadata
        metadata_file = book_folder / "Consolidated_Metadata.json"
        if metadata_file.exists():
            print(f"\n  📊 Indexing Consolidated Metadata...")
            self.index_consolidated_metadata(book_name, metadata_file)
        
        print(f"\n✅ Completed indexing {book_name}")
        print("=" * 60)
    
    def index_all_books(self):
        """Index all books in the output directory"""
        book_folders = [d for d in self.output_dir.iterdir() if d.is_dir()]
        
        if not book_folders:
            print("No book folders found to index")
            return
        
        print(f"\n🚀 Starting ultra-rich indexing of {len(book_folders)} book(s)...")
        print("=" * 60)
        
        for book_folder in book_folders:
            try:
                self.index_book_folder(book_folder)
            except Exception as e:
                print(f"❌ Error indexing {book_folder.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("🎉 Indexing complete!")
        print(f"📊 Total documents in index: {self.collection.count()}")
        print("=" * 60)
    
    def get_stats(self):
        """Get indexing statistics"""
        total_docs = self.collection.count()
        print(f"\n📊 Index Statistics:")
        print(f"  Total documents: {total_docs}")
        
        if total_docs > 0:
            # Sample documents to show chunk types
            sample = self.collection.peek(limit=min(20, total_docs))
            chunk_types = {}
            if sample and 'metadatas' in sample:
                for metadata in sample['metadatas']:
                    chunk_type = metadata.get('chunk_type', 'unknown')
                    chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            print(f"\n  Chunk type distribution (sample):")
            for chunk_type, count in sorted(chunk_types.items()):
                print(f"    • {chunk_type}: {count}")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    output_dir = "Output"
    db_path = "chroma_db"
    clear_index = False
    
    if len(sys.argv) > 1:
        if "--clear" in sys.argv:
            clear_index = True
        if "--output" in sys.argv:
            idx = sys.argv.index("--output")
            if idx + 1 < len(sys.argv):
                output_dir = sys.argv[idx + 1]
        if "--db" in sys.argv:
            idx = sys.argv.index("--db")
            if idx + 1 < len(sys.argv):
                db_path = sys.argv[idx + 1]
    
    # Initialize indexer
    indexer = UltraRichBookIndexer(output_dir=output_dir, db_path=db_path)
    
    # Clear index if requested
    if clear_index:
        print("\n🗑️  Clearing existing index...")
        indexer.clear_index()
    
    # Index all books
    indexer.index_all_books()
    
    # Show statistics
    indexer.get_stats()
