# app/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from app.langgraph.graph import agent_graph
from app.services.langgraph_store import langgraph_store
from app.services.document_processor import document_processor
from langchain_core.runnables import RunnableConfig
import uuid
import os
import json
import asyncio
import traceback

async def chat_ws(ws: WebSocket, conversation_id: str):
    try:
        await ws.accept()
    except Exception as e:
        return
    
    # Use the conversation_id from the URL parameter
    message_count = 0

    try:
        while True:
            try:
                message = await ws.receive()
            except WebSocketDisconnect:
                raise
            
            data = None
            user_text = None
            message_type = None
            
            if "text" in message:
                text_content = message["text"].strip()
                
                if not text_content:
                    continue
                
                try:
                    data = json.loads(text_content)
                    if isinstance(data, dict) and "type" in data:
                        message_type = data.get("type")
                    else:
                        data = None
                except (json.JSONDecodeError, KeyError):
                    data = None
                
                if data is None:
                    user_text = text_content
                    message_type = "message"
                elif message_type == "message":
                    if "data" in data and isinstance(data["data"], dict):
                        user_text = data["data"].get("text", "").strip()
                    else:
                        user_text = data.get("text", "").strip()
            elif "bytes" in message:
                continue
            else:
                continue
            
            if message_type == "message" and user_text:
                # Check for file attachments in the message
                attachments = []
                file_context = ""

                # Try to find attachments in multiple possible locations
                if data and isinstance(data, dict):
                    # Try data["data"]["attachments"] first
                    if "data" in data and isinstance(data["data"], dict) and "attachments" in data["data"]:
                        attachments = data["data"].get("attachments", [])
                    # Try data["attachments"] as fallback
                    elif "attachments" in data:
                        attachments = data.get("attachments", [])
                        print(f"Found attachments in data['attachments']: {len(attachments)} files")
                    else:
                        print(f"No attachments found in data. Data keys: {list(data.keys())}")
                    
                    # Process attachments and extract content
                    for attachment in attachments:
                        file_path = attachment.get("file_path")
                        file_name = attachment.get("file_name", "file")
                        file_type = attachment.get("file_type", "unknown")
                                                
                        if file_path and os.path.exists(file_path):
                            try:
                                # Read processed content
                                result = document_processor.process_file(
                                    file_path, 
                                    attachment.get("mime_type", "text/plain")
                                )
                                
                                if result["content"]:
                                    if file_type == "image":
                                        file_context += f"\n\n[Image: {file_name}]\n(Image data available for vision analysis)\n"
                                    else:
                                        # Add document content to context
                                        content_preview = result['content'][:200] if len(result['content']) > 200 else result['content']
                                        file_context += f"\n\n[Document: {file_name}]\nContent:\n{result['content'][:5000]}\n"  # Limit to 5000 chars
                                
                            except Exception as e:
                                print(f"Error processing attachment: {e}")
                
                # Combine user text with file context for agent processing
                full_user_input = user_text
                has_attachments = False
                attachment_count = 0
                
                if file_context:
                    full_user_input = f"{user_text}\n\nAttached files:{file_context}"
                    has_attachments = True
                    attachment_count = len(attachments)
                
                # Store ORIGINAL user message in LangGraph Store (not the full context)
                # This ensures the UI shows clean messages after refresh
                try:
                    await langgraph_store.add_memory(
                        conversation_id=conversation_id,
                        text=user_text,  # Store original message only
                        sender="user",
                        metadata={
                            "has_attachments": has_attachments,
                            "attachment_count": attachment_count
                        }
                    )
                    
                    message_count += 1
                except Exception as e:
                    print(f"Storage error: {e}")
                
                # Process through LangGraph agent with checkpointing
                try:
                    # RETRIEVE CONVERSATION HISTORY (Short-term memory)
                    recent_memories = await langgraph_store.get_recent_memories(
                        conversation_id=conversation_id,
                        limit=20  # Last 20 messages
                    )
                    
                    # Convert to conversation history format
                    conversation_history = []
                    for mem in recent_memories:
                        conversation_history.append({
                            "role": mem["sender"],  # "user" or "agent"
                            "content": mem["text"]
                        })
                    
                    # OPTIONAL: Search for relevant semantic memories (Long-term memory)
                    # This helps agent remember context from earlier in the conversation
                    semantic_memories = await langgraph_store.search_memories(
                        conversation_id=conversation_id,
                        query=user_text,
                        limit=5  # Top 5 most relevant memories
                    )
                    
                    state = {
                        "user_input": full_user_input,  # Include file context
                        "conversation_id": conversation_id,
                        "conversation_history": conversation_history,  # Now populated!
                        "semantic_context": semantic_memories,  # Relevant past context
                        "response": ""
                    }
                    
                    # **NEW: Use checkpointer with thread_id**
                    config = RunnableConfig(
                        configurable={"thread_id": conversation_id}
                    )
                    
                    # Run agent graph and get response
                    message_id = str(uuid.uuid4())
                    
                    try:
                        print(f"Processing request...")
                        result = await agent_graph.ainvoke(state, config)
                        response_text = result.get("response", "I'm sorry, I couldn't process that request.")
                        
                        # Send response with streaming effect
                        await ws.send_json({
                            "type": "stream_start",
                            "data": {
                                "id": message_id,
                                "sender": "agent"
                            }
                        })
                        
                        # Stream response character by character for better UX
                        for char in response_text:
                            await ws.send_json({
                                "type": "stream_token",
                                "data": {
                                    "id": message_id,
                                    "token": char
                                }
                            })
                            
                            # Small delay between characters (human typing speed)
                            await asyncio.sleep(0.00)    
                        
                        # Send final message
                        await ws.send_json({
                            "type": "stream_end",
                            "data": {
                                "id": message_id,
                                "text": response_text,
                                "sender": "agent"
                            }
                        })
                        
                    except Exception as e:
                        print(f"Traceback:\n{traceback.format_exc()}")
                        
                        response_text = "I'm sorry, I couldn't process that request."
                        
                        await ws.send_json({
                            "type": "message",
                            "data": {
                                "id": message_id,
                                "text": response_text,
                                "sender": "agent",
                                "timestamp": None
                            }
                        })
                   
                    if response_text == "__RATE_LIMIT_ERROR__":
                        response_text = "I'm currently experiencing high demand. Please try again in a few minutes!"
                    elif response_text == "__LLM_ERROR__":
                        response_text = "I'm sorry, I encountered an error. Please try again."
                    
                    # Store agent response in LangGraph Store
                    try:
                        await langgraph_store.add_memory(
                            conversation_id=conversation_id,
                            text=response_text,
                            sender="agent"
                        )
                        
                        message_count += 1
                        
                        # Cleanup old memories periodically
                        if message_count % 100 == 0:
                            deleted = await langgraph_store.delete_old_memories(
                                conversation_id=conversation_id,
                                days=30
                            )
                            print(f"Cleaned up {deleted} old memories")
                            
                    except Exception as e:
                        print(f"Agent storage error: {e}")
                    
                    # Response already sent via streaming (stream_end or fallback message)
                    # No need to send again here
                    
                except Exception as e:
                    print(f"Agent error: {type(e).__name__}: {str(e)}")
                    print(f"Traceback:\n{traceback.format_exc()}")
                    
                    error_response = "I'm sorry, I encountered an error. Please try again."
                    try:
                        await ws.send_json({
                            "type": "message",
                            "data": {
                                "id": str(uuid.uuid4()),
                                "text": error_response,
                                "sender": "agent",
                                "timestamp": None
                            }
                        })
                    except WebSocketDisconnect:
                        raise
                    except Exception as send_err:
                        continue
                
                # Cleanup uploaded files after processing
                if attachments:
                    for attachment in attachments:
                        file_path = attachment.get("file_path")
                        if file_path:
                            try:
                                document_processor.cleanup_file(file_path)
                            except Exception as e:
                                print(f"Error cleaning up file: {e}")
            
            elif message_type == "ping":
                await ws.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.close()
        except:
            pass