from sentence_transformers import CrossEncoder
from typing import List, Dict, Any
import numpy as np


class ContextReranker:
    """
    Reranks retrieved contexts using a cross-encoder model for better relevance scoring.
    Cross-encoders are more accurate than bi-encoders for ranking as they consider
    the query-document interaction directly.
    """
    
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize the reranker with a cross-encoder model.
        
        Args:
            model_name: Name of the cross-encoder model to use
                       Default: ms-marco-MiniLM-L-6-v2 (fast and accurate)
        """
        print(f"Loading reranker model: {model_name}...")
        self.model = CrossEncoder(model_name)
        print("Reranker model loaded successfully!")
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.
        
        Args:
            query: The search query
            documents: List of document dictionaries with 'text' and 'metadata'
            top_k: Number of top documents to return
        
        Returns:
            List of top_k most relevant documents with updated relevance scores
        """
        if not documents:
            return []
        
        # Prepare query-document pairs for cross-encoder
        pairs = [[query, doc['text']] for doc in documents]
        
        # Get relevance scores from cross-encoder
        scores = self.model.predict(pairs)
        
        # Add reranked scores to documents
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)
            # Keep original relevance_score as well
            doc['original_score'] = doc.get('relevance_score', 0.0)
        
        # Sort by rerank score (descending)
        reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        
        # Return top_k documents
        return reranked_docs[:top_k]
    
    def get_relevance_threshold(self, scores: List[float], percentile: float = 50) -> float:
        """
        Calculate a relevance threshold based on score distribution.
        
        Args:
            scores: List of relevance scores
            percentile: Percentile to use as threshold (default: 50th percentile)
        
        Returns:
            Threshold score
        """
        if not scores:
            return 0.0
        return float(np.percentile(scores, percentile))


if __name__ == "__main__":
    # Simple test
    reranker = ContextReranker()
    
    test_query = "What is temple architecture?"
    test_docs = [
        {
            'text': 'Temple architecture follows sacred geometry and divine proportions.',
            'metadata': {'book': 'Test Book', 'chapter': '1'},
            'relevance_score': 0.7
        },
        {
            'text': 'The weather today is sunny and warm.',
            'metadata': {'book': 'Test Book', 'chapter': '2'},
            'relevance_score': 0.6
        },
        {
            'text': 'Agama Shastra describes detailed principles for temple construction.',
            'metadata': {'book': 'Test Book', 'chapter': '3'},
            'relevance_score': 0.65
        }
    ]
    
    print("\nOriginal order:")
    for i, doc in enumerate(test_docs, 1):
        print(f"{i}. Score: {doc['relevance_score']:.3f} - {doc['text'][:50]}...")
    
    reranked = reranker.rerank(test_query, test_docs, top_k=2)
    
    print("\nReranked order (top 2):")
    for i, doc in enumerate(reranked, 1):
        print(f"{i}. Rerank Score: {doc['rerank_score']:.3f} - {doc['text'][:50]}...")
