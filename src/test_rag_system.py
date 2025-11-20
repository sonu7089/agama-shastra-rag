"""
Test script for the RAG system
This script tests basic functionality without requiring actual data
"""

import os
import sys
from pathlib import Path


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import chromadb
        print("  ✓ chromadb")
    except ImportError as e:
        print(f"  ✗ chromadb: {e}")
        return False
    
    try:
        import sentence_transformers
        print("  ✓ sentence-transformers")
    except ImportError as e:
        print(f"  ✗ sentence-transformers: {e}")
        return False
    
    try:
        import streamlit
        print("  ✓ streamlit")
    except ImportError as e:
        print(f"  ✗ streamlit: {e}")
        return False
    
    try:
        import google.generativeai
        print("  ✓ google-generativeai")
    except ImportError as e:
        print(f"  ✗ google-generativeai: {e}")
        return False
    
    try:
        import PyPDF2
        print("  ✓ PyPDF2")
    except ImportError as e:
        print(f"  ✗ PyPDF2: {e}")
        return False
    
    try:
        import tqdm
        print("  ✓ tqdm")
    except ImportError as e:
        print(f"  ✗ tqdm: {e}")
        return False
    
    return True


def test_project_structure():
    """Test that all required files exist"""
    print("\nTesting project structure...")
    
    required_files = [
        "book_enrichment.py",
        "indexer.py",
        "retriever.py",
        "app.py",
        "rag_utils.py",
        "requirements.txt",
        "README.md",
        "RAG_README.md",
        ".env.example"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (missing)")
            all_exist = False
    
    return all_exist


def test_embedding_model():
    """Test that embedding model can be loaded"""
    print("\nTesting embedding model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("  Loading model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test encoding
        test_text = "This is a test sentence."
        embedding = model.encode([test_text])
        
        print(f"  ✓ Model loaded successfully")
        print(f"  ✓ Embedding dimension: {len(embedding[0])}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load model: {e}")
        return False


def test_chromadb():
    """Test ChromaDB functionality"""
    print("\nTesting ChromaDB...")
    
    try:
        import chromadb
        
        # Create temporary client
        client = chromadb.Client()
        
        # Create collection
        collection = client.create_collection(
            name="test_collection",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Add test data
        collection.add(
            embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            documents=["doc1", "doc2"],
            metadatas=[{"type": "test1"}, {"type": "test2"}],
            ids=["id1", "id2"]
        )
        
        # Query
        results = collection.query(
            query_embeddings=[[1.0, 2.0, 3.0]],
            n_results=1
        )
        
        print(f"  ✓ ChromaDB initialized")
        print(f"  ✓ Data added and queried successfully")
        return True
    except Exception as e:
        print(f"  ✗ ChromaDB test failed: {e}")
        return False


def test_environment():
    """Test environment configuration"""
    print("\nTesting environment...")
    
    has_env = Path(".env").exists()
    if has_env:
        print("  ✓ .env file exists")
    else:
        print("  ⚠ .env file not found (you can create it from .env.example)")
    
    has_example = Path(".env.example").exists()
    if has_example:
        print("  ✓ .env.example exists")
    else:
        print("  ✗ .env.example missing")
    
    # Check for API key
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        print("  ✓ GEMINI_API_KEY configured")
    else:
        print("  ⚠ GEMINI_API_KEY not configured")
    
    return True


def test_output_directory():
    """Test if output directory exists and has data"""
    print("\nTesting output directory...")
    
    output_dir = Path("Output")
    if not output_dir.exists():
        print("  ⚠ Output directory not found")
        print("    Run book_enrichment.py to extract book data")
        return False
    
    print("  ✓ Output directory exists")
    
    # Count book folders
    book_folders = [d for d in output_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if book_folders:
        print(f"  ✓ Found {len(book_folders)} book folder(s)")
        
        for book_folder in book_folders:
            chapter_count = len(list(book_folder.glob("Chapter_*.json")))
            print(f"    - {book_folder.name}: {chapter_count} chapters")
    else:
        print("  ⚠ No book folders found")
        print("    Run book_enrichment.py to extract book data")
    
    return True


def test_index():
    """Test if vector index exists"""
    print("\nTesting vector index...")
    
    db_path = Path("chroma_db")
    if not db_path.exists():
        print("  ⚠ Vector database not found")
        print("    Run indexer.py to create the index")
        return False
    
    print("  ✓ Vector database directory exists")
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_collection(name="book_embeddings")
        doc_count = collection.count()
        
        print(f"  ✓ Index loaded successfully")
        print(f"  ✓ Total documents: {doc_count}")
        
        if doc_count == 0:
            print("  ⚠ Index is empty, run indexer.py to index your books")
        
        return True
    except Exception as e:
        print(f"  ⚠ Could not load index: {e}")
        print("    Run indexer.py to create the index")
        return False


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("  RAG System Test Suite")
    print("="*60)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Project Structure", test_project_structure()))
    results.append(("Environment", test_environment()))
    results.append(("Embedding Model", test_embedding_model()))
    results.append(("ChromaDB", test_chromadb()))
    results.append(("Output Directory", test_output_directory()))
    results.append(("Vector Index", test_index()))
    
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    print()
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  {test_name}")
    
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("  🎉 All tests passed! Your system is ready to use.")
    else:
        print("  ⚠️  Some tests failed. Please address the issues above.")
    
    print("="*60)
    print()
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
