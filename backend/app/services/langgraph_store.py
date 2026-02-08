# app/services/langgraph_store.py
from langgraph.store.mongodb import MongoDBStore
from app.config.settings import settings
from app.services.embeddings import embedding_service
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from app.services.embeddings import langchain_embeddings

class LangGraphStoreService:
    """
    Service for managing LangGraph's MongoDB Store.
    This handles long-term memory and semantic search.
    """
    
    def __init__(self):
        try:
            # Create MongoDB client and get collection
            client = MongoClient(settings.MONGODB_URI)
            db = client[settings.MONGODB_DB_NAME]
            collection = db["langgraph_store"]
            
            # Initialize MongoDB Store with vector index configuration for semantic search
            self.store = MongoDBStore(
                collection=collection,
                index_config={
                    "name": "vector_index",  # Atlas Vector Search index name
                    "fields": ["embedding"],  # Field containing embeddings
                    "embed": langchain_embeddings.embed_documents,  # Your embedding service
                    "relevance_score_fn": "cosine",  # Similarity function
                    "filters": [],  
                    "dims": 384,  # Updated to match all-MiniLM-L6-v2 model
                    # Required field - empty list means no additional filters
                },
                auto_index_timeout=120,
            )
            self._available = True
            print("LangGraph MongoDB Store initialized with vector search")
        except Exception as e:
            print(f"LangGraph Store initialization failed: {e}")
            import traceback
            print(traceback.format_exc())
            self.store = None
            self._available = False
    
    async def add_memory(
        self,
        conversation_id: str,
        text: str,
        sender: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Add a memory to the store with embedding for semantic search.
        
        Args:
            conversation_id: Conversation namespace
            text: Message text
            sender: "user" or "agent"
            metadata: Additional metadata
        
        Returns:
            Item key or None
        """
        if not self._available:
            return None
        
        try:
            # Create embedding for semantic search
            embedding = embedding_service.create_embedding(text)
            
            # Create unique key
            timestamp = datetime.utcnow().isoformat()
            key = f"{sender}_{timestamp}"
            
            # Prepare value with embedding
            value = {
                "text": text,
                "sender": sender,
                "timestamp": timestamp,
                "embedding": embedding,
                "metadata": metadata or {}
            }
            
            # Store in MongoDB using LangGraph Store
            # Namespace = conversation_id for isolation
            await self.store.aput(
                namespace=(conversation_id, "memories"),
                key=key,
                value=value
            )
            
            return key
            
        except Exception as e:
            print(f"Error adding memory: {e}")
            return None
    
    async def search_memories(
        self,
        conversation_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories.
        
        Args:
            conversation_id: Conversation namespace
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching memories with scores
        """
        if not self._available:
            return []
        
        try:
            # Search using vector similarity
            results = await self.store.asearch(
                (conversation_id,),
                query=query,
                limit=limit
            )
            
            # Format results
            memories = []
            for item in results:
                if item.value:
                    memories.append({
                        "key": item.key,
                        "text": item.value.get("text", ""),
                        "sender": item.value.get("sender", "unknown"),
                        "timestamp": item.value.get("timestamp", ""),
                        "score": item.score if hasattr(item, 'score') else 0.0,
                        "metadata": item.value.get("metadata", {})
                    })
            
            return memories
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    async def get_recent_memories(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories from a conversation.
        
        Args:
            conversation_id: Conversation namespace
            limit: Maximum results
        
        Returns:
            List of recent memories
        """
        if not self._available:
            return []
        
        try:
            # List all items in namespace
            results = await self.store.asearch(
                (conversation_id, "memories"),
                limit=limit
            )
            
            # Convert to list and sort by timestamp
            memories = []
            for item in results:
                if item.value:
                    memories.append({
                        "key": item.key,
                        "text": item.value.get("text", ""),
                        "sender": item.value.get("sender", "unknown"),
                        "timestamp": item.value.get("timestamp", ""),
                        "metadata": item.value.get("metadata", {})
                    })
            
            # Sort by timestamp (ascending - oldest first for chronological chat display)
            memories.sort(key=lambda x: x.get("timestamp", ""), reverse=False)
            
            return memories[:limit]
            
        except Exception as e:
            print(f"Error getting recent memories: {e}")
            return []
    
    async def delete_old_memories(
        self,
        conversation_id: str,
        days: int = 30
    ) -> int:
        """
        Delete memories older than specified days.
        
        Args:
            conversation_id: Conversation namespace
            days: Age threshold in days
        
        Returns:
            Number of deleted memories
        """
        if not self._available:
            return 0
        
        try:
            from datetime import timedelta
            
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get all memories
            results = await self.store.asearch(
                (conversation_id, "memories"),
                limit=1000
            )
            
            deleted_count = 0
            for item in results:
                if item.value:
                    timestamp = item.value.get("timestamp", "")
                    if timestamp < cutoff:
                        await self.store.adelete(
                            namespace=(conversation_id, "memories"),
                            key=item.key
                        )
                        deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting old memories: {e}")
            return 0

# Singleton instance
langgraph_store = LangGraphStoreService()