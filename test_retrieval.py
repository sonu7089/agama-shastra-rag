"""
Test Retrieval Script
Test what data is being retrieved for different queries
"""
import os
from dotenv import load_dotenv
from retriever import BookRetriever

# Load environment variables
load_dotenv()

def test_query(retriever, query, n_results=5):
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
    
    # Display each result
    for idx, result in enumerate(results, 1):
        print(f"\n{'─'*80}")
        print(f"CHUNK {idx}")
        print(f"{'─'*80}")
        
        # Metadata
        metadata = result.get('metadata', {})
        print(f"📚 Book: {metadata.get('book_name', 'Unknown')}")
        print(f"📖 Chapter: {metadata.get('chapter_number', 'N/A')} - {metadata.get('chapter_title', 'N/A')}")
        print(f"📄 Type: {metadata.get('chunk_type', 'Unknown')}")
        print(f"📍 Pages: {metadata.get('page_range', 'N/A')}")
        
        # Scores
        print(f"\n📊 Scores:")
        print(f"   Original Score: {result.get('original_score', result.get('relevance_score', 0)):.4f}")
        if 'rerank_score' in result:
            print(f"   Rerank Score: {result.get('rerank_score', 0):.4f}")
        
        # Content preview
        text = result.get('text', '')
        preview_length = 300
        if len(text) > preview_length:
            preview = text[:preview_length] + "..."
        else:
            preview = text
        
        print(f"\n📝 Content Preview:")
        print(f"{preview}")
        
        # Keywords if available
        if 'keywords' in metadata and metadata['keywords']:
            keywords = metadata['keywords'].split(',') if isinstance(metadata['keywords'], str) else metadata['keywords']
            print(f"\n🏷️  Keywords: {', '.join(keywords[:5])}")
    
    print("\n" + "="*80)


def main():
    print("="*80)
    print("RAG RETRIEVAL TEST")
    print("="*80)
    
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
        "Who are the main deities mentioned?"
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
                test_query(retriever, query)
                input("\nPress Enter to continue to next query...")
        elif choice == str(len(test_queries) + 1):
            # Custom query
            custom = input("Enter your query: ").strip()
            if custom:
                test_query(retriever, custom)
        else:
            # Specific query
            idx = int(choice) - 1
            if 0 <= idx < len(test_queries):
                test_query(retriever, test_queries[idx])
            else:
                print("Invalid choice!")
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
