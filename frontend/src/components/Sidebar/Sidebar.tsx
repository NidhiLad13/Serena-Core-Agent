import React, { useState } from 'react';
import '../../common/styles/Sidebar.css';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface SidebarProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat?: (id: string) => void;
  onToggleSidebar?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversationId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onToggleSidebar,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (onDeleteChat && confirm('Delete this conversation?')) {
      onDeleteChat(id);
    }
  };

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        {onToggleSidebar && (
          <button
            className="sidebar-toggle-icon-btn"
            onClick={onToggleSidebar}
            title="Close sidebar"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </button>
        )}
        <button className="new-chat-btn" onClick={onNewChat} title="New Chat">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="sidebar-search">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          type="text"
          placeholder="Search chats"
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Chat History */}
      <div className="sidebar-chats">
        <h3>Your chats</h3>
        <div className="chat-list">
          {filteredConversations.length === 0 ? (
            <div className="empty-chats">
              {searchQuery ? 'No chats found' : 'No conversations yet'}
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <div
                key={conv.id}
                className={`chat-item ${currentConversationId === conv.id ? 'active' : ''}`}
                onClick={() => onSelectChat(conv.id)}
              >
                <div className="chat-item-content">
                  <span className="chat-title">{conv.title}</span>
                  {/* <span className="chat-count">{conv.message_count}</span> */}
                </div>
                {onDeleteChat && (
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDelete(e, conv.id)}
                    aria-label="Delete conversation"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* User Profile */}
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">N</div>
          <div className="user-info">
            <div className="user-name">Nidhi Lad</div>
            <div className="user-plan">Free</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;

