"""
LLM service for specialized agents with tool support.
Each agent gets its own set of tools based on its domain.
"""
from app.config.settings import settings
from typing import List, Dict, Any
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from app.services.agent_tools import (
    ORDER_TOOLS,
    PRODUCT_TOOLS,
    BILLING_TOOLS,
    ACCOUNT_TOOLS
)

# Initialize ChatGroq
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    groq_api_key=settings.GROQ_API_KEY,
    temperature=0.7
)

# Agent to tools mapping
AGENT_TOOLS_MAP = {
    "order_agent": ORDER_TOOLS,
    "product_agent": PRODUCT_TOOLS,
    "billing_agent": BILLING_TOOLS,
    "account_agent": ACCOUNT_TOOLS,
}


def create_agent_with_tools(agent_name: str, system_prompt: str):
    """
    Create a LangChain agent with agent-specific tools.
    
    Args:
        agent_name: Name of the agent (order_agent, product_agent, etc.)
        system_prompt: System prompt for the agent
    
    Returns:
        Compiled agent graph that can be invoked
    """
    tools = AGENT_TOOLS_MAP.get(agent_name, [])
    
    if not tools:
        raise ValueError(f"No tools found for agent: {agent_name}")
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt
    )
    
    return agent_graph


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


def generate_with_agent(
    agent_name: str,
    text: str,
    conversation_history: List[Dict[str, str]] = None,
    system_prompt: str = None
) -> str:
    """
    Generate a response using a specialized agent with its tools.
    
    Args:
        agent_name: Name of the specialized agent (order_agent, product_agent, etc.)
        text: The current user input
        conversation_history: List of previous messages
        system_prompt: System prompt for the agent
    
    Returns:
        The generated response text
    """
    try:
        # Create agent with agent-specific tools
        agent_graph = create_agent_with_tools(agent_name, system_prompt)
        
        # Build messages list
        messages = []
        
        # Add conversation history (last 10 messages)
        if conversation_history:
            recent_history = conversation_history[-10:]
            messages.extend(convert_history_to_langchain_messages(recent_history))
        
        # Add current user input
        messages.append(HumanMessage(content=text))
        
        # Invoke the agent
        result = agent_graph.invoke({"messages": messages})
        
        # Extract the final message
        if isinstance(result, dict) and "messages" in result:
            final_messages = result["messages"]
            if final_messages:
                last_message = final_messages[-1]
                if hasattr(last_message, 'content'):
                    response_content = last_message.content.strip()
                    
                    # LangChain sometimes prepends agent_name to responses
                    if response_content.startswith(agent_name):
                        # Remove "agent_name" or "agent_nameagent_name" prefix
                        response_content = response_content.replace(agent_name, "", 1).strip()
                    
                    return response_content
        
        return "__LLM_ERROR__"
    
    except Exception as e:
        print(f"Agent Error: {type(e).__name__}: {str(e)}")
        
        # Handle rate limit errors
        error_str = str(e).upper()
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "QUOTA" in error_str or "RATE" in error_str:
            print("Rate limit detected")
            return "__RATE_LIMIT_ERROR__"
        
        return "__LLM_ERROR__"

