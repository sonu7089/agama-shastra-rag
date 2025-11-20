import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional


class BookRetriever:
    def __init__(self, db_path: str = "chroma_db"):
        self.db_path = db_path
        
        # Initialize embedding model
        print("Loading embedding model for retrieval (EmbeddingGemma-300M)...")
        self.embedding_model = SentenceTransformer('google/embeddinggemma-300m')
        
        # Initialize ChromaDB
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_collection(name="book_embeddings")
            print(f"Connected to database. Total documents: {self.collection.count()}")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            print("Please run indexer.py first to create the index.")
            raise
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        filter_by: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: The search query
            n_results: Number of results to return
            filter_by: Optional metadata filters (e.g., {'book_name': 'BookName', 'chunk_type': 'chapter_summary'})
        
        Returns:
            Dictionary containing results with documents, metadata, and distances
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Build where clause for filtering
        where_clause = None
        if filter_by:
            where_clause = filter_by
        
        # Query the collection
        try:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=where_clause
            )
            return results
        except Exception as e:
            print(f"Error during retrieval: {e}")
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    def retrieve_with_context(
        self,
        query: str,
        n_results: int = 5,
        filter_by: Optional[Dict[str, str]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents and format them with context
        
        Returns:
            List of dictionaries with 'text', 'metadata', and 'relevance_score'
        """
        results = self.retrieve(query, n_results, filter_by)
        
        formatted_results = []
        
        if results and 'documents' in results and results['documents']:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results else [{}] * len(documents)
            distances = results['distances'][0] if 'distances' in results else [0] * len(documents)
            
            for doc, metadata, distance in zip(documents, metadatas, distances):
                # Convert distance to similarity score (1 - distance for cosine)
                similarity = 1 - distance
                
                result = {
                    'text': doc,
                    'relevance_score': similarity,
                }
                
                if include_metadata:
                    result['metadata'] = metadata
                
                formatted_results.append(result)
        
        return formatted_results
    
    def retrieve_with_reranking(
        self,
        query: str,
        n_results: int = 5,
        initial_k: int = 15,
        filter_by: Optional[Dict[str, str]] = None,
        use_reranker: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Intelligent retrieval with reranking for better relevance.
        
        Process:
        1. Retrieve initial_k candidates (more than needed)
        2. Rerank using cross-encoder for precise relevance
        3. Return top n_results most relevant chunks
        
        Args:
            query: Search query
            n_results: Number of final results to return
            initial_k: Number of initial candidates to retrieve (should be > n_results)
            filter_by: Optional metadata filters
            use_reranker: Whether to use cross-encoder reranking
        
        Returns:
            List of top n_results most relevant documents
        """
        # Retrieve more candidates than needed
        candidates = self.retrieve_with_context(
            query, 
            n_results=initial_k, 
            filter_by=filter_by
        )
        
        if not candidates:
            return []
        
        # If reranking is disabled or we have fewer candidates than needed, return as-is
        if not use_reranker or len(candidates) <= n_results:
            return candidates[:n_results]
        
        # Rerank using cross-encoder
        try:
            from reranker import ContextReranker
            
            # Initialize reranker (will be cached in practice)
            if not hasattr(self, '_reranker'):
                self._reranker = ContextReranker()
            
            # Rerank and get top n_results
            reranked = self._reranker.rerank(query, candidates, top_k=n_results)
            return reranked
            
        except Exception as e:
            print(f"Reranking failed: {e}. Falling back to original retrieval.")
            return candidates[:n_results]
    
    def retrieve_by_chunk_type(
        self,
        query: str,
        chunk_type: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents of a specific chunk type
        
        Args:
            query: The search query
            chunk_type: Type of chunk (e.g., 'chapter_summary', 'historical_figure', 'terminology')
            n_results: Number of results to return
        """
        return self.retrieve_with_context(
            query,
            n_results=n_results,
            filter_by={'chunk_type': chunk_type}
        )
    
    def retrieve_from_book(
        self,
        query: str,
        book_name: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from a specific book
        
        Args:
            query: The search query
            book_name: Name of the book to search in
            n_results: Number of results to return
        """
        return self.retrieve_with_context(
            query,
            n_results=n_results,
            filter_by={'book_name': book_name}
        )
    
    def retrieve_from_chapter(
        self,
        query: str,
        book_name: str,
        chapter_number: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from a specific chapter
        
        Args:
            query: The search query
            book_name: Name of the book
            chapter_number: Chapter number to search in
            n_results: Number of results to return
        """
        return self.retrieve_with_context(
            query,
            n_results=n_results,
            filter_by={
                'book_name': book_name,
                'chapter_number': str(chapter_number)
            }
        )
    
    def multi_query_retrieve(
        self,
        queries: List[str],
        n_results_per_query: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents for multiple queries and combine results
        
        Args:
            queries: List of search queries
            n_results_per_query: Number of results per query
        
        Returns:
            Combined and deduplicated results
        """
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.retrieve_with_context(query, n_results=n_results_per_query)
            
            for result in results:
                # Create a simple ID based on text content to avoid duplicates
                result_id = hash(result['text'][:100])
                
                if result_id not in seen_ids:
                    seen_ids.add(result_id)
                    all_results.append(result)
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return all_results
    
    def get_context_for_rag(
        self,
        query: str,
        n_results: int = 5,
        filter_by: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Get formatted context string for RAG pipeline
        
        Returns:
            Formatted context string ready to be used in prompts
        """
        results = self.retrieve_with_context(query, n_results, filter_by)
        
        if not results:
            return "No relevant context found."
        
        context_parts = []
        
        for idx, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            text = result['text']
            score = result['relevance_score']
            
            # Format context with metadata
            context = f"[Context {idx}] (Relevance: {score:.3f})\n"
            
            # Add source information
            if 'book_name' in metadata:
                context += f"Source: {metadata['book_name']}"
                
                if 'chapter_number' in metadata:
                    context += f", Chapter {metadata['chapter_number']}"
                    if 'chapter_title' in metadata:
                        context += f": {metadata['chapter_title']}"
                
                if 'section_title' in metadata:
                    context += f", Section: {metadata['section_title']}"
                
                if 'page_range' in metadata:
                    context += f" (Pages: {metadata['page_range']})"
                
                context += "\n"
            
            # Add chunk type info
            if 'chunk_type' in metadata:
                context += f"Type: {metadata['chunk_type']}\n"
            
            # Add the actual content
            context += f"\n{text}\n"
            
            context_parts.append(context)
        
        return "\n" + "="*80 + "\n".join(context_parts)
    
    def search_terminology(self, term: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for specific terminology (Sanskrit/Hindi terms)"""
        return self.retrieve_by_chunk_type(term, 'terminology', n_results)
    
    def search_historical_figures(self, name: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for historical figures"""
        return self.retrieve_by_chunk_type(name, 'historical_figure', n_results)
    
    def search_events(self, event: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for historical events"""
        return self.retrieve_by_chunk_type(event, 'historical_event', n_results)
    
    def search_locations(self, location: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for geographic locations"""
        return self.retrieve_by_chunk_type(location, 'geographic_location', n_results)
    
    def get_available_books(self) -> List[str]:
        """Get list of all books in the index"""
        try:
            # Get all unique book names
            results = self.collection.get(limit=1000)
            books = set()
            
            if results and 'metadatas' in results:
                for metadata in results['metadatas']:
                    if 'book_name' in metadata:
                        books.add(metadata['book_name'])
            
            return sorted(list(books))
        except Exception as e:
            print(f"Error getting available books: {e}")
            return []


if __name__ == "__main__":
    import sys
    
    # Simple CLI for testing retrieval
    db_path = "chroma_db"
    
    if "--db" in sys.argv:
        idx = sys.argv.index("--db")
        if idx + 1 < len(sys.argv):
            db_path = sys.argv[idx + 1]
    
    retriever = BookRetriever(db_path=db_path)
    
    # Show available books
    print("\nAvailable books:")
    books = retriever.get_available_books()
    for book in books:
        print(f"  - {book}")
    
    # Interactive query loop
    print("\n" + "="*80)
    print("RAG Retrieval System - Interactive Mode")
    print("Enter your queries below. Type 'quit' to exit.")
    print("="*80 + "\n")
    
    while True:
        try:
            query = input("\nQuery: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            print("\nRetrieving relevant context...")
            context = retriever.get_context_for_rag(query, n_results=3)
            print(context)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
