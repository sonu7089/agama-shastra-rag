import os
import json
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
class UltraRichBookIndexer:
    """
    Ultra-Rich Book Indexer
    Creates self-contained, content-rich chunks with inline metadata
    instead of fragmenting data into tiny pieces.
    """
    
    def __init__(self, output_dir: str = "data/outputs/Output", db_path: str = "data/chroma_db"):
        self.output_dir = Path(output_dir)
        self.db_path = db_path
        
        # Initialize embedding model
        print("Loading embedding model (google/embeddinggemma-300m)...")
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
    
    def semantic_chunk_content(self, content: str, max_chars: int = 1800, overlap_chars: int = 200) -> List[str]:
        """
        Split content at semantic boundaries (paragraphs) with overlap.
        
        Args:
            content: Text content to chunk
            max_chars: Maximum characters per chunk
            overlap_chars: Number of characters to overlap between chunks
        
        Returns:
            List of semantically coherent chunks
        """
        if not content or len(content) <= max_chars:
            return [content] if content else []
        
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            # Fallback: split by sentences if no paragraphs
            import re
            sentences = re.split(r'(?<=[.!?])\s+', content)
            paragraphs = sentences
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If single paragraph exceeds max, split it
            if para_size > max_chars:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph into smaller pieces
                words = para.split()
                temp_chunk = []
                temp_size = 0
                
                for word in words:
                    word_size = len(word) + 1
                    if temp_size + word_size > max_chars and temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                        # Keep last few words for overlap
                        overlap_words = temp_chunk[-20:] if len(temp_chunk) > 20 else []
                        temp_chunk = overlap_words + [word]
                        temp_size = sum(len(w) + 1 for w in temp_chunk)
                    else:
                        temp_chunk.append(word)
                        temp_size += word_size
                
                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                continue
            
            # Check if adding this paragraph exceeds limit
            if current_size + para_size + 2 > max_chars and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                
                # Add overlap from previous chunk
                if overlap_chars > 0 and current_chunk:
                    overlap_text = current_chunk[-1][-overlap_chars:] if len(current_chunk[-1]) > overlap_chars else current_chunk[-1]
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size + 2
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for \n\n
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def deduplicate_entities(self, entities: List[Dict], key: str = 'name') -> List[Dict]:
        """
        Remove duplicate entities while preserving first occurrence.
        
        Args:
            entities: List of entity dictionaries
            key: Key to use for deduplication
        
        Returns:
            Deduplicated list of entities
        """
        seen = set()
        unique = []
        
        for entity in entities:
            identifier = str(entity.get(key, '')).lower().strip()
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(entity)
        
        return unique
    
    def analyze_chunk_quality(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Analyze chunk quality and characteristics.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
        
        Returns:
            Dictionary with quality metrics
        """
        if not chunks:
            return {'error': 'No chunks to analyze'}
        
        lengths = [len(chunk['text']) for chunk in chunks]
        
        stats = {
            'total_chunks': len(chunks),
            'avg_length': sum(lengths) / len(lengths),
            'max_length': max(lengths),
            'min_length': min(lengths),
            'median_length': sorted(lengths)[len(lengths) // 2],
            'empty_chunks': sum(1 for l in lengths if l < 50),
            'large_chunks': sum(1 for l in lengths if l > 3000),
            'optimal_chunks': sum(1 for l in lengths if 500 <= l <= 2000),
        }
        
        return stats
    
    def create_cross_reference_chunk(self, chapter_data: Dict, chapter_num: str, book_name: str) -> str:
        """
        Create a cross-reference chunk for entity lookup.
        
        Args:
            chapter_data: Chapter data dictionary
            chapter_num: Chapter number
            book_name: Book name
        
        Returns:
            Cross-reference text for embedding
        """
        chapter_title = chapter_data.get('chapter_title', 'Unknown')
        entities = []
        
        # Collect all entities
        for figure in chapter_data.get('historical_figures', []):
            entities.append(f"{figure.get('name', 'Unknown')} (historical figure, {figure.get('role', 'unknown role')})")
        
        for event in chapter_data.get('historical_events', []):
            entities.append(f"{event.get('event', 'Unknown event')} (event, {event.get('date', 'unknown date')})")
        
        for term in chapter_data.get('sanskrit_hindi_terms', [])[:10]:  # Limit to 10
            entities.append(f"{term.get('term', 'Unknown')} (term, {term.get('translation', 'no translation')})")
        
        for location in chapter_data.get('geographic_locations', [])[:10]:
            entities.append(f"{location.get('place', 'Unknown')} (location)")
        
        if not entities:
            return ""
        
        parts = [
            f"Chapter {chapter_num}: {chapter_title} - Entity Index",
            "",
            "=== ENTITIES DISCUSSED ===",
            '\n'.join(f"• {entity}" for entity in entities),
            "",
            "=== SOURCE ===",
            f"Book: {book_name}, Chapter {chapter_num} (Cross-Reference Index)"
        ]
        
        return '\n'.join(parts)
    
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
    
    
    def batch_add_chunks(self, chunks: List[Dict], batch_size: int = 32):
        """
        Add multiple chunks to the collection in optimized batches.
        
        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of chunks to process at once (optimal for most GPUs/CPUs)
        """
        if not chunks:
            return
        
        total_chunks = len(chunks)
        
        # Process in batches for better memory management
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            ids = [chunk['id'] for chunk in batch]
            texts = [chunk['text'] for chunk in batch]
            metadatas = [chunk['metadata'] for chunk in batch]
            
            # Generate embeddings for this batch
            if total_batches > 1:
                print(f"    Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
            else:
                print(f"    Generating embeddings for {len(batch)} chunks...")
            
            embeddings = self.embedding_model.encode(
                texts, 
                show_progress_bar=False,
                batch_size=min(batch_size, len(texts))
            ).tolist()
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
    
    
    def index_chapter(self, book_name: str, chapter_file: Path):
        """Index a single chapter with ultra-rich chunks and semantic splitting"""
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
                'chunk_type': 'chapter_summary',
                'granularity': 'chapter'
            }
        })
        
        # 2. Add cross-reference chunk for entity lookup
        cross_ref_text = self.create_cross_reference_chunk(chapter_data, chapter_num, book_name)
        if cross_ref_text:
            chunks_to_add.append({
                'id': f"{book_name}_ch{chapter_num}_crossref",
                'text': cross_ref_text,
                'metadata': {
                    'book_name': book_name,
                    'chapter_number': str(chapter_num),
                    'chapter_title': chapter_title,
                    'chunk_type': 'cross_reference',
                    'granularity': 'chapter'
                }
            })
        
        # 3. Index each section with semantic chunking
        for idx, section in enumerate(chapter_data.get('sections', [])):
            section_content = section.get('content', '')
            section_num = section.get('section_number', str(idx))
            section_title = section.get('section_title', 'Unknown')
            
            # Check if section content is too large
            if len(section_content) > 2500:
                # Use semantic chunking for large sections
                content_chunks = self.semantic_chunk_content(section_content, max_chars=1800, overlap_chars=200)
                
                for chunk_idx, content_chunk in enumerate(content_chunks):
                    # Create metadata-enriched chunk
                    chunk_parts = [
                        f"Chapter {chapter_num}: {chapter_title}",
                        f"Section {section_num}: {section_title}",
                        f"Part {chunk_idx + 1} of {len(content_chunks)}",
                        "",
                        "=== CONTENT ===",
                        content_chunk,
                        ""
                    ]
                    
                    # Add summary only to first chunk
                    if chunk_idx == 0 and section.get('summary'):
                        chunk_parts.extend([
                            "=== SECTION SUMMARY ===",
                            section['summary'],
                            ""
                        ])
                    
                    # Add key concepts only to first chunk
                    if chunk_idx == 0 and section.get('key_concepts'):
                        chunk_parts.append("=== KEY CONCEPTS ===")
                        for concept in section['key_concepts'][:5]:
                            chunk_parts.append(f"• {concept}")
                        chunk_parts.append("")
                    
                    # Add relevant terms (deduplicated)
                    section_terms = self.deduplicate_entities(
                        self.extract_section_terms(section, chapter_data), 
                        key='term'
                    )
                    if section_terms and chunk_idx == 0:
                        chunk_parts.append("=== RELEVANT TERMS ===")
                        for term in section_terms[:5]:
                            chunk_parts.append(f"• {term.get('term', '')} - {term.get('translation', '')}")
                        chunk_parts.append("")
                    
                    chunk_parts.extend([
                        "=== SOURCE ===",
                        f"Book: {book_name}, Ch {chapter_num}, Sec {section_num}, Part {chunk_idx + 1}/{len(content_chunks)}, Pages {section.get('page_range', 'N/A')}"
                    ])
                    
                    chunks_to_add.append({
                        'id': f"{book_name}_ch{chapter_num}_sec{idx}_part{chunk_idx}",
                        'text': '\n'.join(chunk_parts),
                        'metadata': {
                            'book_name': book_name,
                            'chapter_number': str(chapter_num),
                            'chapter_title': chapter_title,
                            'section_number': section_num,
                            'section_title': section_title,
                            'chunk_type': 'section_content',
                            'granularity': 'subsection',
                            'part_number': chunk_idx + 1,
                            'total_parts': len(content_chunks),
                            'page_range': section.get('page_range', 'unknown')
                        }
                    })
            else:
                # Use original enriched chunk for smaller sections
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
                        'section_number': section_num,
                        'section_title': section_title,
                        'chunk_type': 'section_content',
                        'granularity': 'section',
                        'page_range': section.get('page_range', 'unknown')
                    }
                })
        
        # 4. Analyze chunk quality
        quality_stats = self.analyze_chunk_quality(chunks_to_add)
        
        # 5. Batch add all chunks
        self.batch_add_chunks(chunks_to_add)
        
        print(f"    ✓ Added {len(chunks_to_add)} chunks for Chapter {chapter_num}")
        print(f"      📊 Avg: {quality_stats['avg_length']:.0f} chars, "
              f"Range: {quality_stats['min_length']}-{quality_stats['max_length']}, "
              f"Optimal: {quality_stats['optimal_chunks']}/{quality_stats['total_chunks']}")
    
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
        """Get comprehensive indexing statistics"""
        total_docs = self.collection.count()
        print(f"\n📊 Index Statistics:")
        print(f"  Total documents: {total_docs}")
        
        if total_docs > 0:
            # Sample more documents for better statistics
            sample_size = min(100, total_docs)
            sample = self.collection.peek(limit=sample_size)
            
            chunk_types = {}
            granularities = {}
            books = set()
            
            if sample and 'metadatas' in sample:
                for metadata in sample['metadatas']:
                    # Count chunk types
                    chunk_type = metadata.get('chunk_type', 'unknown')
                    chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                    
                    # Count granularities
                    granularity = metadata.get('granularity', 'unknown')
                    granularities[granularity] = granularities.get(granularity, 0) + 1
                    
                    # Collect book names
                    if 'book_name' in metadata:
                        books.add(metadata['book_name'])
            
            print(f"\n  📚 Books indexed: {len(books)}")
            for book in sorted(books):
                print(f"    • {book}")
            
            print(f"\n  📑 Chunk type distribution (from {sample_size} sample):")
            for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / sample_size) * 100
                print(f"    • {chunk_type}: {count} ({percentage:.1f}%)")
            
            if granularities and 'unknown' not in granularities or len(granularities) > 1:
                print(f"\n  🔍 Granularity levels:")
                for granularity, count in sorted(granularities.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / sample_size) * 100
                    print(f"    • {granularity}: {count} ({percentage:.1f}%)")
            
            # Analyze chunk sizes from sample
            if sample and 'documents' in sample:
                docs = sample['documents']
                lengths = [len(doc) for doc in docs]
                
                print(f"\n  📏 Chunk size analysis (from {len(docs)} sample):")
                print(f"    • Average: {sum(lengths) / len(lengths):.0f} chars")
                print(f"    • Min: {min(lengths)} chars")
                print(f"    • Max: {max(lengths)} chars")
                print(f"    • Median: {sorted(lengths)[len(lengths) // 2]} chars")
                
                # Quality distribution
                optimal = sum(1 for l in lengths if 500 <= l <= 2000)
                large = sum(1 for l in lengths if l > 2000)
                small = sum(1 for l in lengths if l < 500)
                
                print(f"\n  ✅ Quality distribution:")
                print(f"    • Optimal (500-2000 chars): {optimal} ({(optimal/len(lengths)*100):.1f}%)")
                print(f"    • Large (>2000 chars): {large} ({(large/len(lengths)*100):.1f}%)")
                print(f"    • Small (<500 chars): {small} ({(small/len(lengths)*100):.1f}%)")



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
    indexer = UltraRichBookIndexer(output_dir=output_dir, db_path=db_path)
    
    # Clear index if requested
    if clear_index:
        print("\n🗑️  Clearing existing index...")
        indexer.clear_index()
    
    # Index all books
    indexer.index_all_books()
    
    # Show statistics
    indexer.get_stats()
