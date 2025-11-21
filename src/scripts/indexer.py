import os
import json
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BookIndexer:
    def __init__(self, output_dir: str = "data/outputs/Output", db_path: str = "data/chroma_db"):
        self.output_dir = Path(output_dir)
        self.db_path = db_path
        
        # Initialize embedding model
        print("Loading embedding model (EmbeddingGemma-300M)...")
        hf_token = os.getenv('HF_TOKEN')
        if not hf_token:
            raise ValueError("HF_TOKEN not found in environment variables. Please set it in your .env file.")
        self.embedding_model = SentenceTransformer(
            'google/embeddinggemma-300m', 
            trust_remote_code=True,
            token=hf_token
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="book_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"Indexer initialized. Database path: {db_path}")
    
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
    
    def get_all_book_folders(self) -> List[Path]:
        """Get all book folders from output directory"""
        if not self.output_dir.exists():
            print(f"Output directory {self.output_dir} does not exist")
            return []
        
        book_folders = [d for d in self.output_dir.iterdir() if d.is_dir()]
        print(f"Found {len(book_folders)} book folder(s)")
        return book_folders
    
    def load_json_file(self, file_path: Path) -> Dict:
        """Load JSON file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}
    
    def create_text_for_embedding(self, data: Dict, prefix: str = "") -> str:
        """Create searchable text from various data structures"""
        text_parts = []
        
        if prefix:
            text_parts.append(prefix)
        
        # Add title/section info
        for key in ['chapter_title', 'section_title', 'appendix_title', 'title']:
            if key in data:
                text_parts.append(f"Title: {data[key]}")
        
        # Add summary
        if 'summary' in data:
            text_parts.append(f"Summary: {data['summary']}")
        
        # Add chapter summary
        if 'chapter_summary' in data:
            text_parts.append(f"Summary: {data['chapter_summary']}")
        
        # Add content
        if 'content' in data:
            text_parts.append(f"Content: {data['content']}")
        
        # Add key concepts
        if 'key_concepts' in data:
            text_parts.append(f"Key Concepts: {', '.join(data['key_concepts'])}")
        
        # Add key arguments
        if 'key_arguments' in data:
            text_parts.append(f"Key Arguments: {', '.join(data['key_arguments'])}")
        
        # Add key takeaways
        if 'key_takeaways' in data:
            text_parts.append(f"Key Takeaways: {', '.join(data['key_takeaways'])}")
        
        # Add keywords
        if 'keywords' in data:
            text_parts.append(f"Keywords: {', '.join(data['keywords'])}")
        
        return " ".join(text_parts)
    
    def index_chapter(self, book_name: str, chapter_file: Path):
        """Index a single chapter file"""
        chapter_data = self.load_json_file(chapter_file)
        if not chapter_data:
            return
        
        chapter_num = chapter_data.get('chapter_number', 'unknown')
        chapter_title = chapter_data.get('chapter_title', 'Unknown')
        
        chunks_to_add = []
        
        # 1. Index chapter-level summary
        chapter_summary_text = self.create_text_for_embedding(
            chapter_data,
            prefix=f"Chapter {chapter_num}: {chapter_title}"
        )
        
        chunks_to_add.append({
            'id': f"{book_name}_ch{chapter_num}_summary",
            'text': chapter_summary_text,
            'metadata': {
                'book_name': book_name,
                'chapter_number': str(chapter_num),
                'chapter_title': chapter_title,
                'chunk_type': 'chapter_summary',
                'page_range': f"{chapter_data.get('sections', [{}])[0].get('page_range', 'unknown') if chapter_data.get('sections') else 'unknown'}",
                'keywords': ','.join(chapter_data.get('keywords', []))
            }
        })
        
        # 2. Index each section
        for idx, section in enumerate(chapter_data.get('sections', [])):
            section_text = self.create_text_for_embedding(
                section,
                prefix=f"Chapter {chapter_num}, Section {section.get('section_number', idx)}: {section.get('section_title', '')}"
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
                    'page_range': section.get('page_range', 'unknown'),
                    'keywords': ','.join(section.get('key_concepts', []))
                }
            })
        
        # 3. Index historical figures
        for idx, figure in enumerate(chapter_data.get('historical_figures', [])):
            figure_text = f"Historical Figure: {figure.get('name', '')} - Role: {figure.get('role', '')} - Significance: {figure.get('significance', '')} - Dates: {figure.get('dates', '')}"
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_figure{idx}",
                'text': figure_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'historical_figure',
                    'entity_name': figure.get('name', ''),
                    'entity_role': figure.get('role', ''),
                    'entity_dates': figure.get('dates', '')
                }
            })
        
        # 4. Index historical events
        for idx, event in enumerate(chapter_data.get('historical_events', [])):
            event_text = f"Historical Event: {event.get('event', '')} - Date: {event.get('date', '')} - Significance: {event.get('significance', '')}"
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_event{idx}",
                'text': event_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'historical_event',
                    'event_name': event.get('event', ''),
                    'event_date': event.get('date', '')
                }
            })
        
        # 5. Index geographic locations
        for idx, location in enumerate(chapter_data.get('geographic_locations', [])):
            location_text = f"Geographic Location: {location.get('place', '')} - Context: {location.get('context', '')} - Significance: {location.get('significance', '')}"
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_location{idx}",
                'text': location_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'geographic_location',
                    'location_name': location.get('place', '')
                }
            })
        
        # 6. Index terminology (Sanskrit/Hindi terms)
        for idx, term in enumerate(chapter_data.get('sanskrit_hindi_terms', [])):
            term_text = f"Term: {term.get('term', '')} - Transliteration: {term.get('transliteration', '')} - Translation: {term.get('translation', '')} - Context: {term.get('context', '')}"
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_term{idx}",
                'text': term_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'terminology',
                    'term': term.get('term', ''),
                    'transliteration': term.get('transliteration', ''),
                    'translation': term.get('translation', '')
                }
            })
        
        # 7. Index quotations
        for idx, quote in enumerate(chapter_data.get('quotations', [])):
            quote_text = f"Quotation: {quote.get('quote', '')} - Source: {quote.get('source', '')} - Context: {quote.get('context', '')}"
            
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_quote{idx}",
                'text': quote_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'quotation',
                    'source': quote.get('source', '')
                }
            })
        
        # Add all chunks to collection
        if chunks_to_add:
            texts = [chunk['text'] for chunk in chunks_to_add]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=[chunk['metadata'] for chunk in chunks_to_add],
                ids=[chunk['id'] for chunk in chunks_to_add]
            )
    
    def index_appendix(self, book_name: str, appendix_file: Path):
        """Index a single appendix file"""
        appendix_data = self.load_json_file(appendix_file)
        if not appendix_data:
            return
        
        appendix_id = appendix_data.get('appendix_id', 'unknown')
        appendix_title = appendix_data.get('appendix_title', 'Unknown')
        
        appendix_text = self.create_text_for_embedding(
            appendix_data,
            prefix=f"Appendix {appendix_id}: {appendix_title}"
        )
        
        if appendix_text:
            embedding = self.embedding_model.encode([appendix_text], show_progress_bar=False).tolist()
            
            self.collection.add(
                embeddings=embedding,
                documents=[appendix_text],
                metadatas=[{
                    'book_name': book_name,
                    'appendix_id': str(appendix_id),
                    'appendix_title': appendix_title,
                    'chunk_type': 'appendix',
                    'purpose': appendix_data.get('purpose', '')
                }],
                ids=[f"{book_name}_appendix{appendix_id}"]
            )
    
    def index_references(self, book_name: str, ref_file: Path):
        """Index references and notes"""
        ref_data = self.load_json_file(ref_file)
        if not ref_data:
            return
        
        # Index chapter-specific notes
        for chapter_notes in ref_data.get('notes_by_chapter', []):
            chapter = chapter_notes.get('chapter', 'unknown')
            
            for idx, note in enumerate(chapter_notes.get('notes', [])):
                note_text = f"Reference Note for Chapter {chapter}: {note.get('content', '')} - Citations: {', '.join(note.get('citations', []))}"
                
                embedding = self.embedding_model.encode([note_text], show_progress_bar=False).tolist()
                
                self.collection.add(
                    embeddings=embedding,
                    documents=[note_text],
                    metadatas=[{
                        'book_name': book_name,
                        'chapter_number': str(chapter),
                        'chunk_type': 'reference_note',
                        'note_number': note.get('note_number', str(idx))
                    }],
                    ids=[f"{book_name}_ref_ch{chapter}_note{idx}"]
                )
    
    def index_glossary(self, book_name: str, glossary_file: Path):
        """Index glossary terms"""
        glossary_data = self.load_json_file(glossary_file)
        if not glossary_data:
            return
        
        for idx, term in enumerate(glossary_data.get('terms', [])):
            term_text = f"Glossary Term: {term.get('term', '')} - Original: {term.get('original_script', '')} - Transliteration: {term.get('transliteration', '')} - Definition: {term.get('definition', '')} - Etymology: {term.get('etymology', '')} - Usage: {term.get('usage_context', '')}"
            
            embedding = self.embedding_model.encode([term_text], show_progress_bar=False).tolist()
            
            self.collection.add(
                embeddings=embedding,
                documents=[term_text],
                metadatas=[{
                    'book_name': book_name,
                    'chunk_type': 'glossary_term',
                    'term': term.get('term', ''),
                    'transliteration': term.get('transliteration', '')
                }],
                ids=[f"{book_name}_glossary_term{idx}"]
            )
    
    def index_front_matter(self, book_name: str, front_matter_file: Path):
        """Index front matter (Preface, Foreword, Introduction, etc.)"""
        data = self.load_json_file(front_matter_file)
        if not data:
            return
        
        section_name = front_matter_file.stem
        text = self.create_text_for_embedding(data, prefix=section_name)
        
        if text:
            embedding = self.embedding_model.encode([text], show_progress_bar=False).tolist()
            
            self.collection.add(
                embeddings=embedding,
                documents=[text],
                metadatas=[{
                    'book_name': book_name,
                    'chunk_type': 'front_matter',
                    'section_name': section_name,
                    'page_range': data.get('page_range', 'unknown')
                }],
                ids=[f"{book_name}_{section_name.lower()}"]
            )
    
    def index_book_folder(self, book_folder: Path):
        """Index all files in a book folder"""
        book_name = book_folder.name
        print(f"\nIndexing book: {book_name}")
        
        # Index book structure (optional, for metadata)
        structure_file = book_folder / "book_structure.json"
        if structure_file.exists():
            print(f"  Found book_structure.json")
        
        # Index front matter
        for front_matter in ['Preface.json', 'Foreword.json', 'Acknowledgments.json', 'Introduction.json']:
            front_matter_file = book_folder / front_matter
            if front_matter_file.exists():
                print(f"  Indexing {front_matter}...")
                self.index_front_matter(book_name, front_matter_file)
        
        # Index chapters
        chapter_files = sorted(book_folder.glob("Chapter_*.json"))
        print(f"  Found {len(chapter_files)} chapter(s)")
        for chapter_file in tqdm(chapter_files, desc="  Indexing chapters"):
            self.index_chapter(book_name, chapter_file)
        
        # Index appendixes
        appendix_files = sorted(book_folder.glob("Appendix_*.json"))
        if appendix_files:
            print(f"  Found {len(appendix_files)} appendix(es)")
            for appendix_file in appendix_files:
                print(f"  Indexing {appendix_file.name}...")
                self.index_appendix(book_name, appendix_file)
        
        # Index references
        ref_file = book_folder / "References_and_Notes.json"
        if ref_file.exists():
            print(f"  Indexing References_and_Notes.json...")
            self.index_references(book_name, ref_file)
        
        # Index glossary
        glossary_file = book_folder / "Glossary.json"
        if glossary_file.exists():
            print(f"  Indexing Glossary.json...")
            self.index_glossary(book_name, glossary_file)
        
        print(f"✓ Completed indexing {book_name}")
    
    def index_all_books(self):
        """Index all books in the output directory"""
        book_folders = self.get_all_book_folders()
        
        if not book_folders:
            print("No book folders found to index")
            return
        
        print(f"\nStarting indexing of {len(book_folders)} book(s)...")
        print("=" * 60)
        
        for book_folder in book_folders:
            try:
                self.index_book_folder(book_folder)
            except Exception as e:
                print(f"Error indexing {book_folder.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Indexing complete!")
        print(f"Total documents in index: {self.collection.count()}")
        print("=" * 60)
    
    def get_stats(self):
        """Get indexing statistics"""
        total_docs = self.collection.count()
        print(f"\nIndex Statistics:")
        print(f"  Total documents: {total_docs}")
        
        if total_docs > 0:
            # Sample a few documents to show chunk types
            sample = self.collection.peek(limit=min(10, total_docs))
            chunk_types = set()
            if sample and 'metadatas' in sample:
                for metadata in sample['metadatas']:
                    if 'chunk_type' in metadata:
                        chunk_types.add(metadata['chunk_type'])
            
            print(f"  Chunk types: {', '.join(sorted(chunk_types))}")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    output_dir = "data/outputs/Output"
    db_path = "data/chroma_db"
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
    indexer = BookIndexer(output_dir=output_dir, db_path=db_path)
    
    # Clear index if requested
    if clear_index:
        print("Clearing existing index...")
        indexer.clear_index()
    
    # Index all books
    indexer.index_all_books()
    
    # Show statistics
    indexer.get_stats()
