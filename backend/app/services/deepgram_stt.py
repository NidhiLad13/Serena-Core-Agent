# app/services/deepgram_stt.py
"""
Deepgram Speech-to-Text (STT) Service
Handles real-time audio transcription using Deepgram Live API
"""
import asyncio
import traceback
from typing import Optional
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV1ResultsEvent, ListenV1SpeechStartedEvent
from app.config.settings import settings


class DeepgramSTTService:
    """Service for handling Deepgram Speech-to-Text"""
    
    def __init__(self, api_key: str = None):
        """Initialize Deepgram STT service"""
        self.api_key = api_key or settings.DEEPGRAM_API_KEY
        self.deepgram_client = AsyncDeepgramClient(api_key=self.api_key)
        self.connection = None
        self.transcription_queue = asyncio.Queue()
    
    def connect(
        self,
        model: str = "nova-2",
        language: str = "en-US",
        smart_format: str = "true",
        punctuate: str = "true",
        interim_results: str = "true",
        vad_events: str = "true",
        endpointing: str = "300"
    ):
        """
        Connect to Deepgram Live API for real-time transcription
        Returns the connection context manager
        
        Args:
            model: Deepgram model to use (default: nova-2)
            language: Language code (default: en-US)
            smart_format: Auto-format dates, numbers, etc.
            punctuate: Add punctuation
            interim_results: Return partial results
            vad_events: Voice Activity Detection
            endpointing: Endpoint detection timeout in ms
            
        Returns:
            Async context manager for the connection
        """
        # Normalize parameter types to strings as the SDK expects query params
        def _to_param(v):
            if isinstance(v, bool):
                return "true" if v else "false"
            if v is None:
                return None
            return str(v)

        params = {
            "model": _to_param(model),
            "language": _to_param(language),
            "smart_format": _to_param(smart_format),
            "punctuate": _to_param(punctuate),
            "interim_results": _to_param(interim_results),
            "vad_events": _to_param(vad_events),
            "endpointing": _to_param(endpointing),
        }

        # Debug: print the parameters used for connect (helps diagnose early closes)
        try:
            print(f"Deepgram connect params: {params}")
        except Exception:
            pass

        # Rely on the client-level API key for authentication; do not pass `authorization` here.
        return self.deepgram_client.listen.v1.connect(**{k: v for k, v in params.items() if v is not None})
    
    def setup_event_handlers(self, connection):
        """Set up event handlers for the connection"""
        connection.on(EventType.MESSAGE, self._on_message)
        connection.on(EventType.ERROR, self._on_error)
        connection.on(EventType.OPEN, self._on_open)
        connection.on(EventType.CLOSE, self._on_close)
    
    def _on_message(self, event):
        """Handle transcription messages from Deepgram"""
        try:
            # Handle VAD speech started events (not used for interruption - too sensitive to noise)
            # We only interrupt when actual transcription arrives
            if isinstance(event, ListenV1SpeechStartedEvent):
                # VAD events are logged but not used for interruption
                # to avoid false positives from background noise
                return
            
            # Handle transcription results
            if isinstance(event, ListenV1ResultsEvent):
                if event.channel and event.channel.alternatives and len(event.channel.alternatives) > 0:
                    sentence = event.channel.alternatives[0].transcript
                    if sentence and len(sentence) > 0:
                        is_final = event.is_final if hasattr(event, 'is_final') else True
                        if is_final:
                            # Queue final transcription for processing
                            asyncio.create_task(self.transcription_queue.put(sentence))
        except Exception as e:
            print(f"Error in Deepgram STT callback: {e}")
            traceback.print_exc()
    
    def _on_error(self, error):
        """Handle Deepgram errors"""
        print(f"Deepgram STT error: {error}")
    
    def _on_open(self, event):
        """Handle connection open"""
        print("Deepgram STT WebSocket opened")
    
    def _on_close(self, event):
        """Handle connection close"""
        # Attempt to print close code/reason if available for debugging
        try:
            code = getattr(event, 'code', None)
            reason = getattr(event, 'reason', None)
            if code or reason:
                print(f"Deepgram STT WebSocket closed (code={code}, reason={reason})")
            else:
                print("Deepgram STT WebSocket closed")
        except Exception:
            print("Deepgram STT WebSocket closed")
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to Deepgram for transcription
        
        Args:
            audio_data: Binary audio data (WebM/Opus format)
        """
        if self.connection:
            try:
                await self.connection.send_media(audio_data)
            except Exception as e:
                print(f"Error sending audio to Deepgram STT: {type(e).__name__}: {str(e)}")
                raise
    
    async def get_transcription(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get next transcription from queue
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Transcribed text or None if timeout
        """
        try:
            return await asyncio.wait_for(self.transcription_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
