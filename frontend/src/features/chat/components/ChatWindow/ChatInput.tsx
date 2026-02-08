import React, { useState, useRef, type KeyboardEvent } from 'react';
import '../../styles/ChatInput.css';

interface FileAttachment {
    file_id: string;
    file_name: string;
    file_type: string;
    mime_type: string;
    file_path: string;
}

interface ChatInputProps {
    onSendMessage: (text: string, attachments?: FileAttachment[]) => void;
    disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled = false }) => {
    const [inputValue, setInputValue] = useState('');
    const [attachments, setAttachments] = useState<FileAttachment[]>([]);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSend = () => {
        if (inputValue.trim() || attachments.length > 0) {
            onSendMessage(inputValue, attachments.length > 0 ? attachments : undefined);
            setInputValue('');
            setAttachments([]);
        }
    };

    const handleFileClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setUploading(true);
        try {
            const newAttachments: FileAttachment[] = [];

            for (const file of Array.from(files)) {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('http://localhost:8000/api/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();
                    newAttachments.push({
                        file_id: data.file_id,
                        file_name: data.file_name,
                        file_type: data.file_type,
                        mime_type: data.mime_type,
                        file_path: data.file_path,
                    });
                } else {
                    console.error('Failed to upload file:', file.name);
                    alert(`Failed to upload ${file.name}`);
                }
            }

            setAttachments(prev => [...prev, ...newAttachments]);
        } catch (error) {
            console.error('Error uploading files:', error);
            alert('Error uploading files');
        } finally {
            setUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const removeAttachment = (fileId: string) => {
        setAttachments(prev => prev.filter(att => att.file_id !== fileId));
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    };

    return (
        <div className="chat-input-container">
            {attachments.length > 0 && (
                <div className="attachments-preview">
                    {attachments.map((att) => (
                        <div key={att.file_id} className="attachment-item">
                            <span className="attachment-icon">
                                {att.file_type === 'image' ? '🖼️' : '📄'}
                            </span>
                            <span className="attachment-name">{att.file_name}</span>
                            <button
                                className="remove-attachment"
                                onClick={() => removeAttachment(att.file_id)}
                                aria-label="Remove attachment"
                            >
                                ×
                            </button>
                        </div>
                    ))}
                </div>
            )}
            <div className="input-wrapper">
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    multiple
                    accept="image/*,.pdf,.doc,.docx,.txt,.csv,.md,.json"
                />
                <button
                    className="attach-button"
                    onClick={handleFileClick}
                    disabled={disabled || uploading}
                    aria-label="Attach file"
                    title="Attach images or documents"
                >
                    {uploading ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                <animateTransform
                                    attributeName="transform"
                                    type="rotate"
                                    from="0 12 12"
                                    to="360 12 12"
                                    dur="1s"
                                    repeatCount="indefinite"
                                />
                            </path>
                        </svg>
                    ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    )}
                </button>
                <input
                    type="text"
                    placeholder={disabled ? "Connecting..." : "Type your message..."}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="chat-input-field"
                    disabled={disabled}
                />
                <button
                    className="send-button"
                    onClick={handleSend}
                    disabled={(!inputValue.trim() && attachments.length === 0) || disabled}
                    aria-label="Send message"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </button>
            </div>
            <div className="powered-by">
                Powered by <span>Serena AI</span>
            </div>
        </div>
    );
};

export default ChatInput;
