import React from 'react';
import ChatWindow from './components/ChatWindow/ChatWindow';
import './ChatWidget.css';

const ChatWidget: React.FC = () => {
    return (
        <div className="chat-widget-container full-page">
            <ChatWindow />
        </div>
    );
};

export default ChatWidget;
