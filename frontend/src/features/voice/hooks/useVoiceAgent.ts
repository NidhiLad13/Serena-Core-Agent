// features/voice-agent/hooks/useVoiceAgent.ts
import { useState, useRef, useCallback, useEffect } from 'react';

interface UseVoiceAgentOptions {
  conversationId: string | null;
  onTranscription?: (text: string) => void;
  onAgentResponse?: (text: string) => void;
  onAgentProcessing?: () => void; // Called when agent starts processing
}

export const useVoiceAgent = ({
  conversationId,
  onTranscription,
  onAgentResponse,
  onAgentProcessing,
}: UseVoiceAgentOptions) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioChunksBufferRef = useRef<Uint8Array[]>([]);
  const isReceivingTTSRef = useRef<boolean>(false);
  const currentAudioSourceRef = useRef<AudioBufferSourceNode | null>(null);

  const [isMuted, setIsMuted] = useState(false);
  const isMutedRef = useRef(false);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => {
      const newState = !prev;
      isMutedRef.current = newState;
      return newState;
    });
  }, []);

  // Function to stop current audio playback
  const stopCurrentAudio = useCallback(() => {
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
      } catch {
        // Audio source may already be stopped
      }
      currentAudioSourceRef.current = null;
    }
    // Clear audio buffer
    audioChunksBufferRef.current = [];
  }, []);

  // Connect to backend voice WebSocket
  const connectBackend = useCallback(() => {
    if (!conversationId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/voice/${conversationId}`);

    // Set binary type to arraybuffer for receiving audio chunks
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      console.log('Voice WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = async (event) => {
      try {
        // Check if message is binary (audio data)
        if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
          // Handle binary audio data from Deepgram TTS
          if (isReceivingTTSRef.current) {
            const arrayBuffer = event.data instanceof Blob
              ? await event.data.arrayBuffer()
              : event.data;
            const uint8Array = new Uint8Array(arrayBuffer);
            audioChunksBufferRef.current.push(uint8Array);
          }
          return;
        }

        // Handle text messages (JSON)
        const data = JSON.parse(event.data);

        if (data.type === 'ready') {
          console.log('Voice agent ready:', data.message);
        } else if (data.type === 'transcription') {
          // Show user transcription
          if (onTranscription) {
            onTranscription(data.text);
          }
          // Agent will start processing after transcription
          if (onAgentProcessing) {
            onAgentProcessing();
          }
        } else if (data.type === 'agent_response') {
          // Display the agent response
          if (onAgentResponse) {
            onAgentResponse(data.text);
          }
        } else if (data.type === 'interrupt') {
          // Interrupt current TTS playback
          stopCurrentAudio();
          isReceivingTTSRef.current = false;
          audioChunksBufferRef.current = [];
          console.log('TTS interrupted');
        } else if (data.type === 'tts_start') {
          // Stop any current audio playback before starting new TTS
          stopCurrentAudio();
          // Start receiving TTS audio chunks
          isReceivingTTSRef.current = true;
          audioChunksBufferRef.current = [];
          console.log('TTS started');
        } else if (data.type === 'tts_end') {
          // All audio chunks received, play the audio
          isReceivingTTSRef.current = false;
          await playTTSAudio();
          console.log('TTS ended');
        } else if (data.type === 'tts_error') {
          console.error('TTS error:', data.message);
          isReceivingTTSRef.current = false;
          audioChunksBufferRef.current = [];
        } else if (data.type === 'error') {
          console.error('Voice agent error:', data.message);
        }
      } catch (error) {
        console.error('Error processing message:', error);
      }
    };

    // Function to play TTS audio using Web Audio API
    const playTTSAudio = async () => {
      try {
        if (audioChunksBufferRef.current.length === 0) {
          return;
        }

        // Combine all audio chunks
        const totalLength = audioChunksBufferRef.current.reduce((sum, chunk) => sum + chunk.length, 0);
        const combinedAudio = new Uint8Array(totalLength);
        let offset = 0;
        for (const chunk of audioChunksBufferRef.current) {
          combinedAudio.set(chunk, offset);
          offset += chunk.length;
        }

        // Initialize AudioContext if needed
        if (!audioContextRef.current) {
          const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
          audioContextRef.current = new AudioContextClass();
        }

        const audioContext = audioContextRef.current;

        // Resume audio context if suspended (required by some browsers)
        if (audioContext.state === 'suspended') {
          await audioContext.resume();
        }

        // Decode audio data (PCM 16-bit, 24kHz)
        // Deepgram TTS returns linear16 PCM data
        const sampleRate = 24000;
        const numChannels = 1; // Mono
        const bytesPerSample = 2; // 16-bit = 2 bytes

        // Convert PCM bytes to Float32Array for Web Audio API
        const numSamples = combinedAudio.length / bytesPerSample;
        const audioBuffer = audioContext.createBuffer(numChannels, numSamples, sampleRate);
        const channelData = audioBuffer.getChannelData(0);

        // Convert 16-bit PCM to float32 (-1.0 to 1.0)
        for (let i = 0; i < numSamples; i++) {
          const sampleIndex = i * bytesPerSample;
          // Read 16-bit signed integer (little-endian)
          const int16 = (combinedAudio[sampleIndex + 1] << 8) | combinedAudio[sampleIndex];
          // Convert to signed (-32768 to 32767)
          const signedInt16 = int16 > 32767 ? int16 - 65536 : int16;
          // Normalize to -1.0 to 1.0
          channelData[i] = signedInt16 / 32768.0;
        }

        // Stop any current audio before playing new audio
        stopCurrentAudio();

        // Play the audio
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);

        // Store reference to current audio source so it can be stopped
        currentAudioSourceRef.current = source;

        // Clear source reference when playback ends
        source.onended = () => {
          currentAudioSourceRef.current = null;
        };

        source.start(0);

        // Clear buffer after playing
        audioChunksBufferRef.current = [];

      } catch (error) {
        console.error('Error playing TTS audio:', error);
        audioChunksBufferRef.current = [];
      }
    };

    ws.onerror = (error) => {
      console.error('Voice WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Voice WebSocket closed');
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, [conversationId, onTranscription, onAgentResponse, onAgentProcessing, stopCurrentAudio]);

  // Start recording
  const startRecording = useCallback(async () => {
    // Stop any current TTS playback when user starts speaking
    stopCurrentAudio();
    isReceivingTTSRef.current = false;
    isReceivingTTSRef.current = false;
    audioChunksBufferRef.current = [];

    // Reset mute state
    setIsMuted(false);
    isMutedRef.current = false;

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;

      // Connect to backend (which handles Deepgram)
      connectBackend();

      // Wait a bit for WebSocket to connect
      await new Promise(resolve => setTimeout(resolve, 500));

      // Create MediaRecorder to capture audio
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN && !isMutedRef.current) {
          // Send audio chunks to backend as binary
          wsRef.current.send(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Cleanup
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Start recording with small chunks for real-time streaming
      mediaRecorder.start(100); // Send data every 100ms
      setIsRecording(true);

    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  }, [connectBackend, stopCurrentAudio]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }

    if (wsRef.current) {
      // Send stop signal
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
      wsRef.current.close();
      wsRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Stop any ongoing TTS audio
    stopCurrentAudio();

    if (audioContextRef.current) {
      try {
        // Stop all sources
        audioContextRef.current.close();
        audioContextRef.current = null;
      } catch {
        // Ignore errors when closing
      }
    }
    audioChunksBufferRef.current = [];
    isReceivingTTSRef.current = false;
  }, [isRecording, stopCurrentAudio]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cleanup all resources on unmount
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      stopCurrentAudio();
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close();
        } catch {
          // Ignore errors
        }
      }
      audioChunksBufferRef.current = [];
      isReceivingTTSRef.current = false;
    };
  }, [stopCurrentAudio]); // Include stopCurrentAudio in dependencies

  return {
    isRecording,
    isConnected,
    startRecording,
    stopRecording,
    isMuted,
    toggleMute,
  };
};

