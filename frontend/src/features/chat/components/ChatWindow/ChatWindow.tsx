import React, { useState, useCallback } from 'react';
import ChatHeader from './ChatHeader';
import ChatMessages, { type Message } from './ChatMessages';
import ChatInput from './ChatInput';
import { useChatSocket } from '../../hooks/useChatSocket';
import { useVoiceAgent } from '../../../voice/hooks/useVoiceAgent';
import VoiceButton from '../../../voice/components/VoiceButton/VoiceButton';
import aiLogo from '../../../../assets/ai-logo.png';
import '../../styles/ChatWindow.css';

interface FileAttachment {
    file_id: string;
    file_name: string;
    file_type: string;
    mime_type: string;
    file_path: string;
}

interface ChatWindowProps {
    conversationId?: string | null;
    onConversationUpdate?: () => void;
    isSidebarVisible?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId, onConversationUpdate, isSidebarVisible = true }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const wasConnectedRef = React.useRef(false);
    const [isLoadingMessages, setIsLoadingMessages] = useState(false);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

    // Batch streaming tokens for performance
    const streamBufferRef = React.useRef<{ messageId: string, tokens: string[] }>({ messageId: '', tokens: [] });
    const streamTimerRef = React.useRef<number | null>(null);

    // Load messages when conversation changes
    React.useEffect(() => {
        const loadMessages = async () => {
            if (!conversationId) {
                setMessages([]);
                return;
            }

            setIsLoadingMessages(true);
            try {
                const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`);
                if (response.ok) {
                    const data = await response.json();
                    const loadedMessages: Message[] = data.map((msg: {
                        id: string;
                        text: string;
                        sender: string;
                        timestamp: string;
                        has_attachments?: boolean;
                        attachment_count?: number;
                    }) => {
                        let displayText = msg.text;

                        // Clean up old messages that have "Attached files:" section
                        // This handles messages saved before the fix
                        if (displayText.includes('\n\nAttached files:')) {
                            // Extract only the part before "Attached files:"
                            const parts = displayText.split('\n\nAttached files:');
                            displayText = parts[0];

                            // Count how many attachments by looking for [Document:] or [Image:]
                            const attachmentMatches = parts[1]?.match(/\[(Document|Image):/g);
                            const count = attachmentMatches ? attachmentMatches.length : 1;

                            // Append clean indicator
                            displayText = `${displayText}\n\n📎 ${count} file(s) attached`;
                        }
                        // For new messages with metadata, append indicator
                        else if (msg.has_attachments && msg.attachment_count && msg.attachment_count > 0) {
                            displayText = `${msg.text}\n\n📎 ${msg.attachment_count} file(s) attached`;
                        }

                        return {
                            id: msg.id,
                            text: displayText,
                            sender: msg.sender,
                            timestamp: new Date(msg.timestamp)
                        };
                    });
                    setMessages(loadedMessages);
                } else {
                    console.warn(`Failed to load messages, status: ${response.status}`);
                }
            } catch (error) {
                console.error('Failed to load messages:', error);
                setMessages([]);
            } finally {
                setIsLoadingMessages(false);
            }
        };

        loadMessages();
    }, [conversationId]);

    // Cleanup stream timer on unmount
    React.useEffect(() => {
        return () => {
            if (streamTimerRef.current) {
                clearTimeout(streamTimerRef.current);
            }
        };
    }, []);

    const handleMessage = useCallback((message: Message) => {
        setMessages((prev) => [...prev, message]);
        // Stop showing loading indicator when agent responds
        if (message.sender === 'agent') {
            setIsWaitingForResponse(false);
        }
    }, []);

    // Flush buffered tokens to UI
    const flushStreamBuffer = useCallback(() => {
        if (streamBufferRef.current.tokens.length > 0) {
            const tokensToAdd = streamBufferRef.current.tokens.join('');
            const messageId = streamBufferRef.current.messageId;

            setMessages((prev) => {
                const lastIndex = prev.length - 1;
                const lastMessage = prev[lastIndex];

                if (lastMessage && lastMessage.id === messageId && lastMessage.isStreaming) {
                    const updatedMessage = {
                        ...lastMessage,
                        text: lastMessage.text + tokensToAdd
                    };
                    return [...prev.slice(0, lastIndex), updatedMessage];
                }
                return prev;
            });

            // Clear buffer
            streamBufferRef.current.tokens = [];
        }
    }, []);

    const handleStreamEvent = useCallback((event: {
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
    }) => {
        if (event.type === 'stream_start') {
            // Clear any existing buffer
            if (streamTimerRef.current) {
                clearTimeout(streamTimerRef.current);
                streamTimerRef.current = null;
            }
            streamBufferRef.current = { messageId: event.data.id, tokens: [] };

            // Create a new streaming message
            const streamingMessage: Message = {
                id: event.data.id,
                text: '',
                sender: 'agent',
                timestamp: new Date(),
                isStreaming: true
            };
            setMessages((prev) => [...prev, streamingMessage]);
            setIsWaitingForResponse(false);

        } else if (event.type === 'stream_token') {
            // Buffer tokens instead of immediate update
            if (event.data.token) {
                streamBufferRef.current.messageId = event.data.id;
                streamBufferRef.current.tokens.push(event.data.token);

                // Schedule flush if not already scheduled
                if (!streamTimerRef.current) {
                    streamTimerRef.current = setTimeout(() => {
                        flushStreamBuffer();
                        streamTimerRef.current = null;
                    }, 50); // Batch every 50ms for smooth animation
                }
            }

        } else if (event.type === 'stream_end') {
            // Flush any remaining buffered tokens
            if (streamTimerRef.current) {
                clearTimeout(streamTimerRef.current);
                streamTimerRef.current = null;
            }
            flushStreamBuffer();

            // Finalize the streaming message
            setMessages((prev) => {
                const lastIndex = prev.length - 1;
                const lastMessage = prev[lastIndex];

                if (lastMessage && lastMessage.id === event.data.id) {
                    const updatedMessage = {
                        ...lastMessage,
                        isStreaming: false,
                        text: event.data.text || lastMessage.text
                    };
                    return [...prev.slice(0, lastIndex), updatedMessage];
                }
                return prev;
            });

        } else if (event.type === 'stream_tool_call') {
            console.log(`Tool called: ${event.data.tool_name}`, event.data.tool_args);
        }
    }, [flushStreamBuffer]);

    const { isConnected, isConnecting, sendMessage } = useChatSocket({
        conversationId: conversationId,
        onMessage: handleMessage,
        onStreamEvent: handleStreamEvent,
        onError: () => {
            // Only log, don't show user error here - onclose will handle connection failures
            // This prevents duplicate error messages
        },
        onClose: () => {
            // Only show error message if we were previously connected
            // This prevents showing errors during initial connection attempts
            if (wasConnectedRef.current) {
                const errorMessage: Message = {
                    id: Date.now().toString(),
                    text: 'Connection lost. Attempting to reconnect...',
                    sender: 'agent',
                    timestamp: new Date()
                };
                setMessages((prev) => [...prev, errorMessage]);
            }
            wasConnectedRef.current = false;
        },
        onOpen: () => {
            wasConnectedRef.current = true;
        },
    });

    // Voice agent integration
    const { isRecording, startRecording, stopRecording, isMuted, toggleMute } = useVoiceAgent({
        conversationId: conversationId || null,
        onTranscription: (text: string) => {
            // Add user transcription as a message
            const userMessage: Message = {
                id: Date.now().toString(),
                text: text,
                sender: 'user',
                timestamp: new Date()
            };
            setMessages((prev) => [...prev, userMessage]);
        },
        onAgentResponse: (text: string) => {
            // Hide typing indicator
            setIsWaitingForResponse(false);
            // Add agent voice response as a message
            const agentMessage: Message = {
                id: Date.now().toString(),
                text: text,
                sender: 'agent',
                timestamp: new Date()
            };
            setMessages((prev) => [...prev, agentMessage]);
        },
        onAgentProcessing: () => {
            // Show typing indicator when agent starts processing
            setIsWaitingForResponse(true);
        },
    });

    const handleVoiceToggle = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };


    const handleSendMessage = (text: string, attachments?: FileAttachment[]) => {
        // Add user message to UI immediately
        const displayText = text + (attachments && attachments.length > 0
            ? `\n\n📎 ${attachments.length} file(s) attached`
            : '');

        const userMessage: Message = {
            id: Date.now().toString(),
            text: displayText,
            sender: 'user',
            timestamp: new Date()
        };
        setMessages((prev) => [...prev, userMessage]);

        // Prepare message data with attachments
        const messageData = {
            type: 'message',
            data: {
                text: text,
                attachments: attachments
            }
        };

        // Send message via WebSocket
        if (!sendMessage(JSON.stringify(messageData))) {
            // If not connected, show error message
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: 'Unable to send message. Please check your connection.',
                sender: 'agent',
                timestamp: new Date()
            };
            setMessages((prev) => [...prev, errorMessage]);
            setIsWaitingForResponse(false);
        } else {
            // Show loading indicator while waiting for response
            setIsWaitingForResponse(true);
            // Notify parent to update conversation list
            if (onConversationUpdate) {
                setTimeout(() => onConversationUpdate(), 1000);
            }
        }
    };

    return (
        <div className="chat-window">
            <ChatHeader isConnected={isConnected} isSidebarVisible={isSidebarVisible} />
            {isConnecting && (
                <div className="connection-status">
                    Connecting...
                </div>
            )}
            {!isConnected && !isConnecting && (
                <div className="connection-status error">
                    Disconnected. Attempting to reconnect...
                </div>
            )}

            {isLoadingMessages ? (
                <div className="loading-messages">
                    <div className="spinner"></div>
                    <div>Loading messages...</div>
                </div>
            ) : messages.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-content">
                        <div className="agent-logo-large">
                            <img src={aiLogo} alt="SerenaAI Agent" />
                        </div>
                        {/* <div className="voice-button-container">
                            <VoiceButton
                                isRecording={isRecording}
                                onClick={handleVoiceToggle}
                                disabled={!isConnected}
                            />
                            <p className="voice-hint">Click to start voice conversation</p>
                        </div> */}
                        <div className="suggestion-cards">
                            <button className="suggestion-card" onClick={() => handleSendMessage("What is the weather forecast?")}>
                                <span className="card-icon">☀️</span>
                                <span className="card-title">Weather<br />Forecast</span>
                            </button>
                            <button className="suggestion-card" onClick={() => handleSendMessage("Check market prices")}>
                                <span className="card-icon">💰</span>
                                <span className="card-title">Market<br />Prices</span>
                            </button>
                            <button className="suggestion-card" onClick={() => handleSendMessage("Get crop advice")}>
                                <span className="card-icon">🌱</span>
                                <span className="card-title">Crop<br />Advice</span>
                            </button>
                            <button className="suggestion-card" onClick={() => handleSendMessage("Pest control tips")}>
                                <span className="card-icon">🐛</span>
                                <span className="card-title">Pest<br />Control</span>
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <ChatMessages messages={messages} isWaitingForResponse={isWaitingForResponse} />
            )}

            <div className="chat-footer">
                <div className="footer-content">
                    <div className="input-with-voice">
                        <ChatInput onSendMessage={handleSendMessage} disabled={!isConnected} />
                        <VoiceButton
                            isRecording={isRecording}
                            onClick={handleVoiceToggle}
                            disabled={!isConnected}
                            isMuted={isMuted}
                            onToggleMute={toggleMute}
                        />
                    </div>
                </div>
                <div className="footer-links">
                    <a href="#">Home</a>
                    <span>|</span>
                    <span>© 2026 SerenaAI</span>
                </div>
            </div>

        </div>
    );
};

export default ChatWindow;
