"""
Simple LLM service for the Main Orchestrator (Router).
This is used only for intent classification without tools.
For agent-specific tool calling, see llm_agent.py
"""
from app.config.settings import settings
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Initialize ChatGroq
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    groq_api_key=settings.GROQ_API_KEY,
    temperature=0.7
)


def convert_history_to_langchain_messages(conversation_history: List[Dict[str, str]]) -> List:
    """
    Convert conversation history to LangChain message format.
    
    Args:
        conversation_history: List of messages with 'role' and 'content'
    
    Returns:
        List of LangChain message objects
    """
    if not conversation_history:
        return []
    
    messages = []
    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ["assistant", "agent"]:
            messages.append(AIMessage(content=content))
    
    return messages


def generate(
    text: str, 
    conversation_history: List[Dict[str, str]] = None, 
    system_prompt: str = None
) -> str:
    """
    Generate a simple LLM response without tools.
    Used by the Main Orchestrator for intent classification.
    
    Args:
        text: The current user input
        conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        system_prompt: Optional system prompt to guide the LLM
    
    Returns:
        The generated response text
    """
    try:
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # Add conversation history (last 10 messages)
        if conversation_history:
            recent_history = conversation_history[-10:]
            messages.extend(convert_history_to_langchain_messages(recent_history))
        
        # Add current user input
        messages.append(HumanMessage(content=text))
        
        # Generate response
        response = llm.invoke(messages)
        
        if hasattr(response, 'content') and response.content:
            return response.content.strip()
        else:
            return "__LLM_ERROR__"
    
    except Exception as e:
        # Log the actual error for debugging
        print(f"LLM Error: {type(e).__name__}: {str(e)}")
        
        # Handle rate limit errors specifically (429 or RESOURCE_EXHAUSTED)
        error_str = str(e).upper()
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "QUOTA" in error_str or "RATE" in error_str:
            print("Rate limit detected")
            return "__RATE_LIMIT_ERROR__"
        
        return "__LLM_ERROR__"
