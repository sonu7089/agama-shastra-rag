"""
Test Retrieval Script
Test what data is being retrieved for different queries
"""
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import sys
# Add src directory to python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from retriever import BookRetriever

# Load environment variables
load_dotenv()

def test_query(retriever, query, n_results=5, output_file=None):
    """Test a single query and display results"""
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    print("="*80)
    
    # Test with reranking (intelligent retrieval)
    print("\n🔍 RETRIEVING WITH INTELLIGENT RERANKING...")
    results = retriever.retrieve_with_reranking(
        query,
        n_results=n_results,
        initial_k=15  # Retrieve 15, rerank to top 5
    )
    
    if not results:
        print("❌ No results found!")
        return
    
    print(f"\n✅ Retrieved {len(results)} chunks\n")
    
    # Prepare output content if file is provided
    output_lines = []
    if output_file:
        output_lines.append("=" * 80)
        output_lines.append(f"QUERY: {query}")
        output_lines.append("=" * 80)
        output_lines.append(f"\nRetrieved {len(results)} chunks\n")
    
    # Display each result
    for idx, result in enumerate(results, 1):
        chunk_display = []
        
        print(f"\n{'─'*80}")
        print(f"CHUNK {idx}")
        print(f"{'─'*80}")
        
        chunk_display.append(f"\n{'─'*80}")
        chunk_display.append(f"CHUNK {idx}")
        chunk_display.append(f"{'─'*80}")
        
        # Metadata
        metadata = result.get('metadata', {})
        book_info = f"📚 Book: {metadata.get('book_name', 'Unknown')}"
        chapter_info = f"📖 Chapter: {metadata.get('chapter_number', 'N/A')} - {metadata.get('chapter_title', 'N/A')}"
        type_info = f"📄 Type: {metadata.get('chunk_type', 'Unknown')}"
        page_info = f"📍 Pages: {metadata.get('page_range', 'N/A')}"
        
        print(book_info)
        print(chapter_info)
        print(type_info)
        print(page_info)
        
        chunk_display.append(book_info)
        chunk_display.append(chapter_info)
        chunk_display.append(type_info)
        chunk_display.append(page_info)
        
        # Scores
        score_header = f"\n📊 Scores:"
        orig_score = f"   Original Score: {result.get('original_score', result.get('relevance_score', 0)):.4f}"
        print(score_header)
        print(orig_score)
        
        chunk_display.append(score_header)
        chunk_display.append(orig_score)
        
        if 'rerank_score' in result:
            rerank_score = f"   Rerank Score: {result.get('rerank_score', 0):.4f}"
            print(rerank_score)
            chunk_display.append(rerank_score)
        
        # Full content (not just preview)
        text = result.get('text', '')
        
        # For console: show preview
        preview_length = 300
        if len(text) > preview_length:
            preview = text[:preview_length] + "..."
        else:
            preview = text
        
        print(f"\n📝 Content Preview:")
        print(f"{preview}")
        
        # For file: show FULL content
        chunk_display.append(f"\n📝 FULL CONTENT:")
        chunk_display.append("─" * 80)
        chunk_display.append(text)
        chunk_display.append("─" * 80)
        
        # Keywords if available
        if 'keywords' in metadata and metadata['keywords']:
            keywords = metadata['keywords'].split(',') if isinstance(metadata['keywords'], str) else metadata['keywords']
            keyword_info = f"\n🏷️  Keywords: {', '.join(keywords[:5])}"
            print(keyword_info)
            chunk_display.append(keyword_info)
        
        # Add to output
        if output_file:
            output_lines.extend(chunk_display)
    
    print("\n" + "=" * 80)
    
    # Write to file if provided
    if output_file:
        output_lines.append("\n" + "=" * 80)
        output_lines.append("\n\n")
        
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        print(f"\n💾 Context saved to: {output_file}")



def main():
    print("="*80)
    print("RAG RETRIEVAL TEST")
    print("="*80)
    
    # Create output directory and file
    output_dir = Path("retrieval_outputs")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"retrieval_context_{timestamp}.txt"
    
    # Write header to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAG RETRIEVAL TEST - FULL CONTEXT EXPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
    
    print(f"\n💾 Output will be saved to: {output_file}")
    
    # Initialize retriever
    db_path = "chroma_db"
    print(f"\n📂 Loading database from: {db_path}")
    retriever = BookRetriever(db_path=db_path)
    
    # Get database stats
    total_docs = retriever.collection.count()
    books = retriever.get_available_books()
    print(f"✅ Database loaded: {total_docs} documents, {len(books)} books")
    print(f"📚 Books: {', '.join(books)}")
    
    # Test queries
    test_queries = [
        "What is the garbhagriha?",
        "What are the principles of temple architecture?",
        "Explain the concept of sacred geometry",
        "What rituals are performed in temples?",
        "Who are the main deities mentioned?", 
        "Who claimed an exclusive right to perform temple worship, defending this with scriptural sanctions, royal patronage, and long-standing tradition? "
    ]
    
    print("\n" + "="*80)
    print("TESTING QUERIES")
    print("="*80)
    
    # Let user choose or test all
    print("\nAvailable test queries:")
    for i, q in enumerate(test_queries, 1):
        print(f"{i}. {q}")
    print(f"{len(test_queries) + 1}. Custom query")
    print(f"{len(test_queries) + 2}. Test all queries")
    
    try:
        choice = input("\nEnter choice (or press Enter to test all): ").strip()
        
        if not choice or choice == str(len(test_queries) + 2):
            # Test all
            for query in test_queries:
                test_query(retriever, query, output_file=output_file)
                input("\nPress Enter to continue to next query...")
        elif choice == str(len(test_queries) + 1):
            # Custom query
            custom = input("Enter your query: ").strip()
            if custom:
                test_query(retriever, custom, output_file=output_file)
        else:
            # Specific query
            idx = int(choice) - 1
            if 0 <= idx < len(test_queries):
                test_query(retriever, test_queries[idx], output_file=output_file)
            else:
                print("Invalid choice!")
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print(f"\n\n{'='*80}")
    print(f"✅ All retrieved context saved to:")
    print(f"   {output_file.absolute()}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
