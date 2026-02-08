import { useEffect, useRef, useState, useCallback } from 'react';
import type { Message } from '../components/ChatWindow/ChatMessages';

interface StreamEvent {
  type: 'stream_start' | 'stream_token' | 'stream_end' | 'stream_tool_call';
  data: {
    id: string;
    token?: string;
    text?: string;
    sender?: string;
    node?: string;
    tool_name?: string;
    tool_args?: Record<string, unknown>;
  };
}

interface UseChatSocketOptions {
  conversationId?: string | null;
  onMessage: (message: Message) => void;
  onStreamEvent?: (event: StreamEvent) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
  onOpen?: () => void;
}

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/chat';

export const useChatSocket = ({
  conversationId,
  onMessage,
  onStreamEvent,
  onError,
  onClose,
  onOpen,
}: UseChatSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const shouldReconnectRef = useRef(true);
  const connectionStartTimeRef = useRef<number | null>(null);
  const isConnectingRef = useRef(false); // Track if we're currently attempting to connect

  // Use refs to store callbacks so they don't cause re-renders
  const onMessageRef = useRef(onMessage);
  const onStreamEventRef = useRef(onStreamEvent);
  const onErrorRef = useRef(onError);
  const onCloseRef = useRef(onClose);
  const onOpenRef = useRef(onOpen);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onStreamEventRef.current = onStreamEvent;
    onErrorRef.current = onError;
    onCloseRef.current = onClose;
    onOpenRef.current = onOpen;
  }, [onMessage, onStreamEvent, onError, onClose, onOpen]);

  const connect = useCallback(() => {
    // Don't connect if no conversation ID
    if (!conversationId) {
      console.log('Cannot connect: No conversation ID');
      return;
    }
  

    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // Clean up any existing connection
    if (wsRef.current) {
      try {
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
      } catch {
        // Ignore error
      }
      wsRef.current = null;
    }

    // Set connecting flag to prevent duplicate attempts
    isConnectingRef.current = true;
    setIsConnecting(true);
    connectionStartTimeRef.current = Date.now();

    try {
      const wsUrl = `${WS_BASE_URL}/${conversationId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected successfully');
        isConnectingRef.current = false;
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttempts.current = 0;
        connectionStartTimeRef.current = Date.now();
        onOpenRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle error messages from backend
          if (data.type === 'error') {
            const errorMessage: Message = {
              id: Date.now().toString(),
              text: data.data?.message || 'An error occurred',
              sender: 'agent',
              timestamp: new Date(),
            };
            onMessageRef.current(errorMessage);
            return;
          }

          // Handle streaming events
          if (data.type === 'stream_start' || data.type === 'stream_token' || 
              data.type === 'stream_end' || data.type === 'stream_tool_call') {
            if (onStreamEventRef.current) {
              onStreamEventRef.current(data as StreamEvent);
            }
            return;
          }

          // Handle regular messages
          if (data.type === 'message' && data.data) {
            const message: Message = {
              id: data.data.id || Date.now().toString(),
              text: data.data.text,
              sender: data.data.sender === 'agent' ? 'agent' : 'user',
              timestamp: data.data.timestamp ? new Date(data.data.timestamp) : new Date(),
            };
            onMessageRef.current(message);
          } else if (data.type === 'pong') {
            // Handle pong for keep-alive
          } else {
            // Unknown message type
          }
        } catch {
          // Try to handle as plain text if JSON parsing fails
          if (typeof event.data === 'string' && event.data.trim()) {
            const message: Message = {
              id: Date.now().toString(),
              text: event.data,
              sender: 'agent',
              timestamp: new Date(),
            };
            onMessageRef.current(message);
          }
        }
      };

      ws.onerror = (error) => {
        const readyState = ws.readyState;
        console.error('WebSocket error:', error, 'ReadyState:', readyState);

        // Only log errors if connection was established or if it's a persistent issue
        // Errors during CONNECTING state are often handled by onclose, so we don't need to log them here
        if (readyState === WebSocket.OPEN || readyState === WebSocket.CLOSING) {
          // Error occurred
        } else {
          // During CONNECTING or CLOSED state, errors are usually handled by onclose
        }

        isConnectingRef.current = false;
        setIsConnecting(false);
        // Don't call onError callback here - let onclose handle the actual error reporting
        // This prevents duplicate error messages
      };

      ws.onclose = () => {
        const connectionDuration = connectionStartTimeRef.current
          ? Date.now() - connectionStartTimeRef.current
          : 0;



        isConnectingRef.current = false;
        setIsConnected(false);
        setIsConnecting(false);
        connectionStartTimeRef.current = null;
        onCloseRef.current?.();

        // Don't reconnect if it was a clean close or if we've exceeded max attempts
        if (!shouldReconnectRef.current) {
          return;
        }

        // If connection closed very quickly (< 1 second), it might be a backend issue
        // Add a longer delay before reconnecting
        const isQuickClose = connectionDuration > 0 && connectionDuration < 1000;
        const baseDelay = isQuickClose ? 5000 : 1000; // 5 seconds for quick closes, 1 second otherwise

        // Attempt to reconnect only if shouldReconnect is true and we haven't exceeded max attempts
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts.current - 1), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (shouldReconnectRef.current) {
              connect();
            }
          }, delay);
        } else {
          // Max reconnection attempts reached
        }
      };

      wsRef.current = ws;
    } catch {
      isConnectingRef.current = false;
      setIsConnecting(false);
      setIsConnected(false);
      // Attempt to reconnect after a delay
      if (shouldReconnectRef.current && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current += 1;
        const delay = 2000;
        reconnectTimeoutRef.current = setTimeout(() => {
          if (shouldReconnectRef.current) {
            connect();
          }
        }, delay);
      }
    }
  }, [conversationId]);

  const sendMessage = useCallback((text: string) => {
    if (!text || !text.trim()) {
      return false;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        // Check if the text is already a JSON message (e.g., with attachments)
        let message: string;
        try {
          const parsed = JSON.parse(text);
          if (parsed.type === 'message' && parsed.data) {
            // Already properly formatted JSON message with data/attachments
            message = text;
          } else {
            // Plain text message, wrap it
            message = JSON.stringify({
              type: 'message',
              text: text.trim(),
            });
          }
        } catch {
          // Not JSON, treat as plain text message
          message = JSON.stringify({
            type: 'message',
            text: text.trim(),
          });
        }
        
        wsRef.current.send(message);
        return true;
      } catch {
        return false;
      }
    } else {
      return false;
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    isConnectingRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      try {
        const ws = wsRef.current;
        const readyState = ws.readyState;

        // Remove event handlers first to prevent them from firing
        ws.onerror = null;
        ws.onclose = null;
        ws.onopen = null;
        ws.onmessage = null;

        // Only close if WebSocket is OPEN
        // If CONNECTING, let it fail naturally (closing during CONNECTING causes browser warning)
        // If already CLOSING or CLOSED, nothing to do
        if (readyState === WebSocket.OPEN) {
          ws.close();
        } else if (readyState === WebSocket.CONNECTING) {
          // For CONNECTING state, we can't safely close without browser warning
          // Just remove handlers and let it fail naturally - the onclose handler won't fire
          // because we've already removed it
        }
      } catch {
        // Ignore errors when closing - WebSocket might already be closed
      }
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  useEffect(() => {
    shouldReconnectRef.current = true;
    
    // Only connect if we have a conversation ID
    if (conversationId) {
      connect();
    }

    return () => {
      // Prevent reconnection attempts
      shouldReconnectRef.current = false;
      isConnectingRef.current = false;

      // Clear any pending reconnection timeouts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Clean up WebSocket connection
      if (wsRef.current) {
        const ws = wsRef.current;
        const readyState = ws.readyState;

        // Remove all event handlers first
        ws.onerror = null;
        ws.onclose = null;
        ws.onopen = null;
        ws.onmessage = null;

        // Only close if WebSocket is OPEN
        // If CONNECTING, don't close (causes browser warning) - let it fail naturally
        // If already CLOSING or CLOSED, nothing to do
        if (readyState === WebSocket.OPEN) {
          try {
            ws.close();
          } catch {
            // Ignore errors - WebSocket might already be closing/closed
          }
        } else if (readyState === WebSocket.CONNECTING) {
          // Don't close during CONNECTING - causes browser warning
          // Handlers are removed, so onclose won't fire even if connection completes
        }
        wsRef.current = null;
      }

      setIsConnected(false);
      setIsConnecting(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]); // Reconnect when conversation ID changes

  return {
    isConnected,
    isConnecting,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
};