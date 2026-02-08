# app/api/voice_websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from app.config.settings import settings
from app.langgraph.graph import agent_graph
from app.services.langgraph_store import langgraph_store
from app.services.deepgram_stt import DeepgramSTTService
from app.services.deepgram_tts import DeepgramTTSService
from langchain_core.runnables import RunnableConfig
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
import json
import asyncio
import traceback
import time

async def voice_ws(ws: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time voice conversation"""
    try:
        await ws.accept()
    except Exception as e:
        return
    
    # Initialize STT and TTS services
    stt_service = DeepgramSTTService()
    tts_service = DeepgramTTSService()
    
    message_count = 0
    transcription_task = None
    stt_task = None
    current_agent_task = None
    current_tts_task = None
    interruption_event = asyncio.Event()
    last_interruption_time = 0.0
    INTERRUPTION_DEBOUNCE_MS = 500  # Minimum 500ms between interruptions
    deepgram_active = False  # Track if Deepgram connection is active
    
    async def interrupt_current_response():
        """Interrupt current agent response and TTS playback - only if agent is actively responding"""
        nonlocal current_agent_task, current_tts_task, interruption_event, last_interruption_time
        
        # Only interrupt if agent is currently responding (processing or speaking)
        agent_is_responding = (
            (current_agent_task and not current_agent_task.done()) or
            (current_tts_task and not current_tts_task.done())
        )
        
        if not agent_is_responding:
            # Agent is not responding, no need to interrupt
            return
        
        # Debounce interruptions to prevent rapid firing
        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - last_interruption_time < INTERRUPTION_DEBOUNCE_MS:
            return  # Skip if too soon since last interruption
        
        last_interruption_time = current_time
        
        # Set interruption event to signal ongoing tasks to stop
        interruption_event.set()
        
        # Cancel ongoing agent processing
        if current_agent_task and not current_agent_task.done():
            current_agent_task.cancel()
            try:
                await current_agent_task
            except asyncio.CancelledError:
                pass
            current_agent_task = None
        
        # Cancel ongoing TTS generation
        if current_tts_task and not current_tts_task.done():
            current_tts_task.cancel()
            try:
                await current_tts_task
            except asyncio.CancelledError:
                pass
            current_tts_task = None
        
        # Send interruption signal to frontend
        try:
            await ws.send_json({
                "type": "interrupt"
            })
        except Exception as e:
            print(f"Error sending interrupt signal: {e}")
    
    async def process_transcription(user_text: str):
        """Process transcribed text through the agent"""
        if not user_text.strip():
            return
        
        # Interrupt any ongoing agent response when new user input arrives
        # (Only interrupts if agent is currently processing or speaking)
        await interrupt_current_response()
        
        try:
            # Send transcription to frontend
            await ws.send_json({
                "type": "transcription",
                "text": user_text
            })
            
            # Store user message
            try:
                await langgraph_store.add_memory(
                    conversation_id=conversation_id,
                    text=user_text,
                    sender="user"
                )
                nonlocal message_count
                message_count += 1
            except Exception as e:
                print(f"Storage error: {e}")
            
            # Process through LangGraph agent
            try:
                # Clear interruption event and check if we should proceed
                # (if another interruption happened, it will be set again)
                was_interrupted = interruption_event.is_set()
                interruption_event.clear()
                
                # If we were interrupted, don't start processing
                if was_interrupted:
                    return
                
                recent_memories = await langgraph_store.get_recent_memories(
                    conversation_id=conversation_id,
                    limit=20
                )
                
                conversation_history = []
                for mem in recent_memories:
                    conversation_history.append({
                        "role": mem["sender"],
                        "content": mem["text"]
                    })
                
                state = {
                    "user_input": user_text,
                    "conversation_id": conversation_id,
                    "conversation_history": conversation_history,
                    "semantic_context": [],
                    "response": ""
                }
                
                config = RunnableConfig(
                    configurable={"thread_id": conversation_id}
                )
                
                # Create task for agent processing so it can be cancelled
                async def run_agent():
                    try:
                        return await agent_graph.ainvoke(state, config)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        print(f"Agent processing error: {e}")
                        raise
                
                current_agent_task = asyncio.create_task(run_agent())
                try:
                    result = await current_agent_task
                except asyncio.CancelledError:
                    # Task was cancelled due to interruption
                    return
                finally:
                    current_agent_task = None
                
                # Check if interrupted after agent processing
                if interruption_event.is_set():
                    return
                
                response_text = result.get("response", "I'm sorry, I couldn't process that request.")
                
                # Store agent response
                try:
                    await langgraph_store.add_memory(
                        conversation_id=conversation_id,
                        text=response_text,
                        sender="agent"
                    )
                    message_count += 1
                except Exception as e:
                    print(f"Agent storage error: {e}")
                
                # Send response text to frontend for display
                await ws.send_json({
                    "type": "agent_response",
                    "text": response_text
                })
                
                # Generate TTS audio using Deepgram TTS service
                try:
                    # Check if interrupted before starting TTS
                    if interruption_event.is_set():
                        return
                    
                    # Send TTS start signal
                    await ws.send_json({
                        "type": "tts_start"
                    })
                    
                    # Create task for TTS generation so it can be cancelled
                    async def generate_tts():
                        try:
                            async for audio_chunk in tts_service.generate_audio(
                                text=response_text,
                                model="aura-asteria-en",
                                encoding="linear16",
                                sample_rate=24000,
                                max_chars=1500,
                                max_sentences=5
                            ):
                                # Check for interruption before sending each chunk
                                if interruption_event.is_set():
                                    break
                                # Send audio chunk to frontend as binary
                                await ws.send_bytes(audio_chunk)
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            print(f"TTS generation error: {e}")
                            raise
                    
                    current_tts_task = asyncio.create_task(generate_tts())
                    try:
                        await current_tts_task
                    except asyncio.CancelledError:
                        # TTS was cancelled due to interruption
                        return
                    finally:
                        current_tts_task = None
                    
                    # Check if interrupted after TTS generation
                    if interruption_event.is_set():
                        return
                    
                    # Send TTS end signal
                    await ws.send_json({
                        "type": "tts_end"
                    })
                except Exception as e:
                    print(f"TTS error: {type(e).__name__}: {str(e)}")
                    print(f"Traceback:\n{traceback.format_exc()}")
                    # Send error signal
                    await ws.send_json({
                        "type": "tts_error",
                        "message": str(e)
                    })
                
            except Exception as e:
                print(f"Agent error: {type(e).__name__}: {str(e)}")
                print(f"Traceback:\n{traceback.format_exc()}")
                
                error_response = "I'm sorry, I encountered an error. Please try again."
                await ws.send_json({
                    "type": "agent_response",
                    "text": error_response
                })
                
                # Generate TTS for error response using TTS service
                try:
                    await ws.send_json({"type": "tts_start"})
                    async for audio_chunk in tts_service.generate_audio(
                        text=error_response,
                        model="aura-asteria-en",
                        encoding="linear16",
                        sample_rate=24000,
                        max_chars=1500,
                        max_sentences=5
                    ):
                        await ws.send_bytes(audio_chunk)
                    await ws.send_json({"type": "tts_end"})
                except Exception as e:
                    print(f"TTS error for error response: {e}")
        except Exception as e:
            print(f"Error processing transcription: {e}")
    
    # Background task to process transcriptions from STT service
    async def process_transcription_queue():
        while True:
            try:
                user_text = await stt_service.get_transcription(timeout=1.0)
                if user_text:
                    await process_transcription(user_text)
            except Exception as e:
                print(f"Error in transcription queue: {e}")
    
    # Start transcription processor
    transcription_task = asyncio.create_task(process_transcription_queue())
    
    # Connect to Deepgram STT service using async context manager
    try:
        print(f"Connecting to Deepgram STT for conversation {conversation_id}...")
        async with stt_service.connect(
            model="nova-2",
            language="en-US",
            smart_format=True,
            punctuate=True,
            interim_results=True,
            vad_events=True,
            endpointing=300
        ) as deepgram_connection:
            stt_service.connection = deepgram_connection
            stt_service.setup_event_handlers(deepgram_connection)
            deepgram_active = True  # Mark connection as active
            
            # Note: We don't use VAD events for interruption because they're too sensitive
            # to background noise. Instead, we only interrupt when actual transcription arrives.
            
            # Start listening
            async def listen_to_deepgram():
                try:
                    print("Starting Deepgram listener...")
                    await deepgram_connection.start_listening()
                except Exception as e:
                    print(f"Error in Deepgram listener: {e}")
                    traceback.print_exc()
            
            stt_task = asyncio.create_task(listen_to_deepgram())
            
            # Wait a bit for connection to establish
            await asyncio.sleep(0.5)
            print("Deepgram STT setup complete, waiting for messages...")
            
            # Send ready message to frontend
            try:
                await ws.send_json({
                    "type": "ready",
                    "message": "Voice agent ready"
                })
                print("Ready message sent to frontend")
            except Exception as e:
                print(f"Error sending ready message: {type(e).__name__}: {str(e)}")
                if hasattr(e, '__traceback__'):
                    traceback.print_exc()
            
            # Main message loop - keep connection alive (INSIDE async with block)
            try:
                while True:
                    try:
                        message = await ws.receive()
                    except WebSocketDisconnect:
                        print("WebSocket disconnected")
                        break
                    
                    # Handle text messages
                    if "text" in message:
                        text_content = message["text"].strip()
                        if not text_content:
                            continue
                        
                        try:
                            data = json.loads(text_content)
                            message_type = data.get("type")
                            
                            if message_type == "stop":
                                # Stop recording
                                print("Received stop signal")
                                break
                            
                            elif message_type == "ping":
                                await ws.send_json({"type": "pong"})
                                
                        except json.JSONDecodeError:
                            continue
                    
                    # Handle binary audio data
                    elif "bytes" in message:
                        audio_data = message["bytes"]
                        
                        # Only send if connection is still active
                        if deepgram_active:
                            try:
                                # Send audio to Deepgram STT service
                                await stt_service.send_audio(audio_data)
                            except ConnectionClosedOK:
                                # Connection closed normally - stop the loop
                                print("Deepgram connection closed normally")
                                deepgram_active = False
                                break
                            except ConnectionClosedError as e:
                                # Connection closed with error
                                print(f"Deepgram connection closed with error: {e}")
                                deepgram_active = False
                                break
                            except Exception as e:
                                # Log other actual errors but continue
                                print(f"Error sending audio to Deepgram STT: {type(e).__name__}: {str(e)}")
                    
            except WebSocketDisconnect:
                print("WebSocket disconnected in main loop")
            except Exception as e:
                print(f"Voice WebSocket error: {e}")
                print(f"Traceback:\n{traceback.format_exc()}")
            finally:
                # Mark connection as inactive
                deepgram_active = False
                
                # Cancel STT task when exiting context
                if stt_task:
                    stt_task.cancel()
                    try:
                        await stt_task
                    except asyncio.CancelledError:
                        pass
        
    except Exception as e:
        print(f"Error setting up Deepgram STT: {e}")
        traceback.print_exc()
        # Send error to frontend
        try:
            await ws.send_json({
                "type": "error",
                "message": f"Failed to connect to Deepgram STT: {str(e)}"
            })
        except:
            pass
    finally:
        # Cancel tasks
        if transcription_task:
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass
        
        try:
            await ws.close()
        except:
            pass