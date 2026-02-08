# app/api/rest.py
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.services.langgraph_store import langgraph_store
from bson import ObjectId
from app.services.mongo import db
from app.services.document_processor import document_processor
import uuid
import os
router = APIRouter()

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

class MessageResponse(BaseModel):
    id: str
    text: str
    sender: str
    timestamp: str
    has_attachments: Optional[bool] = False
    attachment_count: Optional[int] = 0

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(user_id: str = "default"):
    """Get all conversations for a user"""
    try:
        # Get unique conversation IDs from LangGraph Store
        # We'll query the store's namespace collection to find all conversations
        conversations = []
        # Get all unique conversation IDs from memories
        pipeline = [
            {"$sort": {"created_at": 1}},  # Sort by creation time first
            {"$group": {
                "_id": "$namespace",
                "count": {"$sum": 1},
                "first_message": {"$first": "$value.text"},  # Now gets the actual first message
                "created_at": {"$min": "$created_at"},
                "updated_at": {"$max": "$updated_at"}
            }},
            {"$sort": {"updated_at": -1}},  # Sort conversations by most recent
            {"$limit": 50}
        ]
        
        # Debug: Check total documents in collection
        total_docs = db.langgraph_store.count_documents({})
        print(f"Total documents in langgraph_store: {total_docs}")
        
        results = list(db.langgraph_store.aggregate(pipeline))
        print(f"Aggregation returned {len(results)} conversations")
        
        for conv in results:
            # Extract conversation_id from namespace (format: ["conversation_id", "memories"])
            namespace = conv["_id"]
            if isinstance(namespace, list) and len(namespace) >= 1:
                conv_id = namespace[0]  # First element is always the conversation ID
                
                # Generate title from first message (first 50 chars)
                first_msg = conv.get("first_message", "New Chat")
                title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
                
                conversations.append(ConversationResponse(
                    id=conv_id,
                    title=title,
                    created_at=conv["created_at"].isoformat() if isinstance(conv["created_at"], datetime) else str(conv["created_at"]),
                    updated_at=conv["updated_at"].isoformat() if isinstance(conv["updated_at"], datetime) else str(conv["updated_at"]),
                    message_count=conv["count"]
                ))
        
        return conversations
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return []

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: str, limit: int = 100):
    """Get all messages for a specific conversation"""
    try:
        # Fetch memories from LangGraph Store
        memories = await langgraph_store.get_recent_memories(conversation_id, limit=limit)
        
        messages = []
        for mem in memories:
            metadata = mem.get("metadata", {})
            messages.append(MessageResponse(
                id=mem.get("id", str(ObjectId())),
                text=mem["text"],
                sender=mem["sender"],
                timestamp=mem["created_at"].isoformat() if isinstance(mem.get("created_at"), datetime) else datetime.utcnow().isoformat(),
                has_attachments=metadata.get("has_attachments", False),
                attachment_count=metadata.get("attachment_count", 0)
            ))
        
        return messages
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    try:
        # Delete all memories for this conversation (namespace can be [conv_id] or [conv_id, "memories"])
        from app.services.mongo import db
        result = db.langgraph_store.delete_many({
            "namespace.0": conversation_id  # Match first element of namespace array
        })
        
        return {
            "status": "deleted",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a file (image or document)
    Supported: PDF, Word, Text, Images (jpg, png, etc.)
    """
    try:
        # Validate file type
        mime_type = file.content_type
        if not document_processor.is_supported(mime_type):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {mime_type}. Supported types: images (jpg, png, etc.), PDF, Word, Text files."
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(document_processor.upload_dir, unique_filename)
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process file
        result = document_processor.process_file(file_path, mime_type)
        
        return {
            "status": "success",
            "file_id": unique_filename,
            "file_name": file.filename,
            "file_type": result["file_type"],
            "mime_type": mime_type,
            "file_path": file_path,
            "has_content": result["content"] is not None,
            "content_preview": result["content"][:200] if result["content"] and isinstance(result["content"], str) else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

