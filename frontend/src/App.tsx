import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import aiLogo from './assets/ai-logo.png';
import ChatWindow from './features/chat/components/ChatWindow/ChatWindow.tsx'; // Explicitly add .tsx if needed, or just keep as is
// Actually standard import is sufficient
import './common/styles/App.css';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);

  const fetchConversations = React.useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/conversations');
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
        if (!currentConversationId) {
          if (data.length > 0) {
            setCurrentConversationId(data[0].id);
          } else {
            const newConvId = crypto.randomUUID();
            const newConv: Conversation = {
              id: newConvId,
              title: 'New Chat',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              message_count: 0
            };
            setConversations([newConv]);
            setCurrentConversationId(newConvId);
          }
        }
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
      if (conversations.length === 0) {
        const newConvId = crypto.randomUUID();
        const newConv: Conversation = {
          id: newConvId,
          title: 'New Chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: 0
        };
        setConversations([newConv]);
        setCurrentConversationId(newConvId);
      }
    } finally {
      setIsLoading(false);
    }
  }, [currentConversationId, conversations.length]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleNewChat = () => {
    const newConvId = crypto.randomUUID();
    const newConv: Conversation = {
      id: newConvId,
      title: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0
    };
    setConversations(prev => [newConv, ...prev]);
    setCurrentConversationId(newConvId);
  };

  const handleSelectChat = (id: string) => {
    setCurrentConversationId(id);
  };

  const handleDeleteChat = async (id: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/conversations/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setConversations(prev => prev.filter(conv => conv.id !== id));
        if (currentConversationId === id) {
          const remaining = conversations.filter(conv => conv.id !== id);
          setCurrentConversationId(remaining.length > 0 ? remaining[0].id : null);
        }
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleConversationUpdate = React.useCallback(() => {
    setTimeout(() => {
      fetchConversations();
    }, 1000);
  }, [fetchConversations]);

  return (
    <div className="app-container chatgpt-layout">
      <div className={`sidebar-wrapper ${isSidebarVisible ? 'visible' : 'hidden'}`}>
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
          onToggleSidebar={() => setIsSidebarVisible(!isSidebarVisible)}
        />
      </div>

      <div className="main-content">
        {!isSidebarVisible && (
          <button
            className="open-sidebar-btn"
            onClick={() => setIsSidebarVisible(true)}
            title="Open sidebar"
          >
            <img src={aiLogo} alt="Open Sidebar" style={{ width: '90px', height: '90px', objectFit: 'contain' }} />
          </button>
        )}

        {isLoading ? (
          <div className="loading-state">Loading...</div>
        ) : (
          <ChatWindow
            conversationId={currentConversationId}
            onConversationUpdate={handleConversationUpdate}
            isSidebarVisible={isSidebarVisible}
          />
        )}
      </div>
    </div>
  );
}

export default App;
