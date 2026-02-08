# app/services/deepgram_tts.py
"""
Deepgram Text-to-Speech (TTS) Service
Handles text-to-speech conversion using Deepgram TTS API
"""
import re
from typing import AsyncIterator
from deepgram import AsyncDeepgramClient
from app.config.settings import settings


def clean_text_for_tts(text: str) -> str:
    """
    Remove markdown formatting from text for TTS
    
    Args:
        text: Text with markdown formatting
        
    Returns:
        Cleaned text without markdown
    """
    if not text:
        return ''
    
    # Remove markdown bold/italic: **text**, *text*, __text__, _text_
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)  # *italic*
    cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)  # __bold__
    cleaned = re.sub(r'_([^_]+)_', r'\1', cleaned)  # _italic_
    
    # Remove markdown code blocks: `code` and ```code```
    cleaned = re.sub(r'```[\s\S]*?```', '', cleaned)  # Code blocks
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)  # Inline code
    
    # Remove markdown links: [text](url)
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    
    # Remove markdown headers: # Header
    cleaned = re.sub(r'^#{1,6}\s+', '', cleaned, flags=re.MULTILINE)
    
    # Remove markdown lists: - item, * item, 1. item
    cleaned = re.sub(r'^[\s]*[-*+]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\d+\.\s+', '', cleaned, flags=re.MULTILINE)
    
    # Remove markdown images: ![alt](url)
    cleaned = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', cleaned)
    
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Max 2 newlines
    cleaned = cleaned.strip()
    
    return cleaned


def create_short_tts_version(text: str, max_chars: int = 1500, max_sentences: int = 5) -> str:
    """
    Create a short version of text for TTS, truncating at sentence boundaries
    
    Args:
        text: Full text to shorten
        max_chars: Maximum characters (default: 1500, Deepgram limit is 2000)
        max_sentences: Maximum number of sentences (default: 5)
        
    Returns:
        Shortened text suitable for TTS
    """
    if not text:
        return ''
    
    # First clean the text
    cleaned = clean_text_for_tts(text)
    
    # If already short enough, return as is
    if len(cleaned) <= max_chars:
        return cleaned
    
    # Split into sentences (ending with . ! ?)
    sentences = re.split(r'([.!?]+[\s\n]+)', cleaned)
    
    # Recombine sentences with their punctuation
    combined_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            combined_sentences.append(sentences[i] + sentences[i + 1])
        else:
            combined_sentences.append(sentences[i])
    
    # Take first few sentences that fit within max_chars
    result = ''
    for sentence in combined_sentences[:max_sentences]:
        if len(result + sentence) <= max_chars:
            result += sentence
        else:
            break
    
    # If we still have nothing or it's too short, truncate at word boundary
    if not result or len(result) < 100:
        # Truncate at word boundary
        truncated = cleaned[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:  # Only truncate at word if we keep at least 80% of text
            result = truncated[:last_space] + '...'
        else:
            result = truncated + '...'
    else:
        # Remove trailing whitespace
        result = result.rstrip()
    
    return result


class DeepgramTTSService:
    """Service for handling Deepgram Text-to-Speech"""
    
    def __init__(self, api_key: str = None):
        """Initialize Deepgram TTS service"""
        self.api_key = api_key or settings.DEEPGRAM_API_KEY
        self.deepgram_client = AsyncDeepgramClient(api_key=self.api_key)
    
    async def generate_audio(
        self,
        text: str,
        model: str = "aura-asteria-en",
        encoding: str = "linear16",
        sample_rate: int = 24000,
        max_chars: int = 1500,
        max_sentences: int = 5
    ) -> AsyncIterator[bytes]:
        """
        Generate audio from text using Deepgram TTS
        
        Args:
            text: Text to convert to speech
            model: Deepgram TTS model (default: aura-asteria-en)
            encoding: Audio encoding format (default: linear16 - PCM 16-bit)
            sample_rate: Sample rate in Hz (default: 24000)
            max_chars: Maximum characters for TTS (default: 1500)
            max_sentences: Maximum sentences for TTS (default: 5)
            
        Yields:
            Audio chunks as bytes (PCM 16-bit format)
        """
        # Create short version for TTS
        tts_text = create_short_tts_version(text, max_chars=max_chars, max_sentences=max_sentences)
        
        if not tts_text:
            return
        
        # Generate audio using Deepgram TTS
        async for audio_chunk in self.deepgram_client.speak.v1.audio.generate(
            text=tts_text,
            model=model,
            encoding=encoding,
            sample_rate=sample_rate,
        ):
            if audio_chunk:
                yield audio_chunk

