"""
Agent configuration for multi-agent orchestration.
"""
from typing import Dict, Any

# Default agent configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "conversation_history_limit": 10,  # Number of recent messages to include in agent context
}

def get_agent_config() -> Dict[str, Any]:
    """Get the current agent configuration."""
    return DEFAULT_CONFIG.copy()