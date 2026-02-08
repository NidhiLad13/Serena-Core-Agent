import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FaArrowDown } from 'react-icons/fa';
import '../../styles/ChatMessages.css';

export interface Message {
    id: string;
    text: string;
    sender: 'user' | 'agent';
    timestamp: Date;
    isStreaming?: boolean; // New flag to indicate streaming in progress
}

interface ChatMessagesProps {
    messages: Message[];
    isWaitingForResponse?: boolean;
}

const ChatMessages: React.FC<ChatMessagesProps> = React.memo(({ messages, isWaitingForResponse = false }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
        setShowScrollButton(!isNearBottom);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isWaitingForResponse]);

    return (
        <div className="chat-messages" onScroll={handleScroll}>
            <div className="message-list">
                {messages.map((msg) => (
                    <div key={msg.id} className={`message-row ${msg.sender}`}>
                        {msg.sender === 'agent' && (
                            <div className="message-avatar">
                                <img src="https://ui-avatars.com/api/?name=Support+Agent&background=random" alt="Agent" />
                            </div>
                        )}
                        <div className="message-bubble">
                            <div className="message-content">
                                {msg.isStreaming ? (
                                    // Show plain text with inline cursor while streaming
                                    <span className="streaming-text">
                                        {msg.text}
                                        <span className="streaming-cursor">▊</span>
                                    </span>
                                ) : (
                                    // Show formatted markdown after streaming completes
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            // Customize rendering for specific elements
                                            p: ({ children }) => <p className="markdown-p">{children}</p>,
                                            h3: ({ children }) => <h3 className="markdown-h3">{children}</h3>,
                                            ul: ({ children }) => <ul className="markdown-ul">{children}</ul>,
                                            ol: ({ children }) => <ol className="markdown-ol">{children}</ol>,
                                            li: ({ children }) => <li className="markdown-li">{children}</li>,
                                            code: ({ children, className }) => {
                                                const isInline = !className;
                                                return isInline ? (
                                                    <code className="markdown-code-inline">{children}</code>
                                                ) : (
                                                    <code className="markdown-code-block">{children}</code>
                                                );
                                            },
                                            pre: ({ children }) => <pre className="markdown-pre">{children}</pre>,
                                            strong: ({ children }) => <strong className="markdown-strong">{children}</strong>,
                                        }}
                                    >
                                        {msg.text}
                                    </ReactMarkdown>
                                )}
                            </div>
                            <span className="message-time">
                                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                    </div>
                ))}
                {isWaitingForResponse && (
                    <div className="message-row agent loading">
                        <div className="message-avatar">
                            <img src="https://ui-avatars.com/api/?name=Support+Agent&background=random" alt="Agent" />
                        </div>
                        <div className="message-bubble loading-bubble">
                            <div className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            {showScrollButton && (
                <button
                    className="scroll-bottom-btn"
                    onClick={scrollToBottom}
                    aria-label="Scroll to bottom"
                >
                    <FaArrowDown />
                </button>
            )}
        </div>
    );
});

ChatMessages.displayName = 'ChatMessages';

export default ChatMessages;
