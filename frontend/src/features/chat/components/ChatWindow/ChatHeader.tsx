import React from 'react';
import '../../styles/ChatHeader.css';

interface ChatHeaderProps {
    isConnected: boolean;
    isSidebarVisible?: boolean; // Kept for interface compatibility but unused
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ isConnected }) => {
    return (
        <div className="chat-header">
            <div className="header-left">
            </div>
            <div className="header-right">
                <div className="status-badge">
                    <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
                    <span className="status-text">{isConnected ? 'Connected' : 'Disconnected'}</span>
                </div>
            </div>
        </div>
    );
};

export default ChatHeader;
