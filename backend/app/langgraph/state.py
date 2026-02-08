# langgraph/state.py
from typing import TypedDict, List, Dict, Optional, Any

class AgentState(TypedDict):
    user_input: str
    conversation_id: str
    conversation_history: List[Dict[str, str]]  # List of {"role": "user/agent", "content": "..."}
    response: str
    intent: Optional[str]  # Detected intent
    extracted_slots: Optional[Dict]  # Extracted slot values
    missing_slots: Optional[List[str]]  # Missing required slots
    agent_type: Optional[str]  # Which specialized agent to use
    semantic_context: Optional[List[Dict[str, Any]]]  # Semantically relevant past memories for context
