// features/voice-agent/components/VoiceButton/VoiceButton.tsx
import React from 'react';
import '../../styles/VoiceButton.css';

interface VoiceButtonProps {
  isRecording: boolean;
  onClick: () => void;
  disabled?: boolean;
  isMuted?: boolean;
  onToggleMute?: () => void;
}

const VoiceButton: React.FC<VoiceButtonProps> = ({
  isRecording,
  onClick,
  disabled = false,
  isMuted = false,
  onToggleMute
}) => {

  if (isRecording) {
    return (
      <div className="voice-controls-expanded">
        <button
          className={`voice-action-btn mute-btn ${isMuted ? 'muted' : ''}`}
          onClick={(e) => {
            e.stopPropagation();
            onToggleMute?.();
          }}
          title={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="1" y1="1" x2="23" y2="23"></line>
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          )}
        </button>

        <button
          className="voice-action-btn end-btn"
          onClick={onClick}
          title="End conversation"
        >
          <span className="audio-wave-dots">
            <span></span><span></span><span></span><span></span>
          </span>
          <span className="btn-text">End</span>
        </button>
      </div>
    );
  }

  return (
    <button
      className={`voice-button ${isRecording ? 'recording' : ''}`}
      onClick={onClick}
      disabled={disabled}
      aria-label="Start recording"
      title="Start recording"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M12 1C10.34 1 9 2.34 9 4V12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12V4C15 2.34 13.66 1 12 1Z"
          fill="currentColor"
        />
        <path
          d="M19 10V12C19 15.87 15.87 19 12 19C8.13 19 5 15.87 5 12V10H3V12C3 16.97 7.03 21 12 21C16.97 21 21 16.97 21 12V10H19Z"
          fill="currentColor"
        />
      </svg>
    </button>
  );
};

export default VoiceButton;

