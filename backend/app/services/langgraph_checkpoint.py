# app/services/langgraph_checkpoint.py
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from app.config.settings import settings

class LangGraphCheckpointService:
    """
    Service for managing LangGraph's MongoDB Checkpointer.
    This handles conversation state persistence.
    """
    
    def __init__(self):
        try:
            # Create MongoDB client
            client = MongoClient(settings.MONGODB_URI)
            db = client[settings.MONGODB_DB_NAME]
            
            # Initialize MongoDB Checkpointer with sync client
            self.checkpointer = MongoDBSaver(db)
            self._available = True
            print("LangGraph MongoDB Checkpointer initialized")
        except Exception as e:
            print(f"LangGraph Checkpointer initialization failed: {e}")
            self.checkpointer = None
            self._available = False
    
    def get_checkpointer(self):
        """Get the checkpointer instance for LangGraph."""
        return self.checkpointer if self._available else None

# Singleton instance
langgraph_checkpoint = LangGraphCheckpointService()