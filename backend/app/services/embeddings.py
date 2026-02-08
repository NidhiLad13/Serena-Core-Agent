# app/services/embeddings.py
from sentence_transformers import SentenceTransformer
from typing import List, Union

class EmbeddingService:
    def __init__(self):
        # Using a lightweight model for fast inference and quick download
        # 'all-MiniLM-L6-v2' (384 dims) - faster, smaller, good quality
        # 'all-mpnet-base-v2' (768 dims) - larger, slower download, slightly better quality
        print("Loading embedding model: all-MiniLM-L6-v2 (384 dimensions)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimensions = 384
        print("Embedding model loaded successfully!")
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * self.dimensions
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts efficiently."""
        if not texts:
            return []
        
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


# LangChain-compatible wrapper for LangGraph Store
class LangChainEmbeddingsWrapper:
    """
    Wrapper to make EmbeddingService compatible with LangChain's Embeddings interface.
    LangGraph Store expects embed_documents() and embed_query() methods.
    """
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.model = embedding_service.model  # For AutoEmbeddings detection
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (LangChain interface)."""
        return self.embedding_service.create_embeddings_batch(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query (LangChain interface)."""
        return self.embedding_service.create_embedding(text)

# Singleton instances
embedding_service = EmbeddingService()
langchain_embeddings = LangChainEmbeddingsWrapper(embedding_service)