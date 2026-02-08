"""
Main Orchestrator (Router) for multi-agent system.

The router is responsible for:
1. Receiving all user messages
2. Understanding user intent
3. Routing requests to the correct specialized agent
4. The specialized agents handle the actual request and return responses
"""
from typing import Dict
from app.services.llm_gemini import generate


# Intent mapping to agent types
INTENT_TO_AGENT = {
    "order_inquiry": "order_agent",
    "order_status": "order_agent",
    "order_tracking": "order_agent",
    "order_cancellation": "order_agent",
    "order_delivery": "order_agent",
    
    "product_inquiry": "product_agent",
    "product_price": "product_agent",
    "product_availability": "product_agent",
    "product_features": "product_agent",
    "product_specifications": "product_agent",
    
    "billing_inquiry": "billing_agent",
    "invoice_request": "billing_agent",
    "payment_status": "billing_agent",
    "refund_request": "billing_agent",
    
    "account_inquiry": "account_agent",
    "email_update": "account_agent",
    "password_reset": "account_agent",
    "username_update": "account_agent",
    "profile_management": "account_agent",
}


async def classify_intent(state: Dict) -> Dict:
    """
    Main Orchestrator (Router) Node.
    
    This is the entry point for all user messages. The orchestrator:
    1. Receives the user message
    2. Analyzes it to understand the intent
    3. Determines which specialized agent should handle it
    4. Routes to that agent
    
    The orchestrator does NOT answer domain questions directly - it only
    coordinates and delegates to the appropriate specialized agent.
    
    Args:
        state: Current conversation state with user_input
    
    Returns:
        Updated state with intent and agent_type set for routing
    """
    user_input = state["user_input"]
    conversation_history = state.get("conversation_history", [])
    
    # Check if message contains file attachments (indicated by [Document:] or [Image:] markers)
    has_files = "[Document:" in user_input or "[Image:" in user_input or "Attached files:" in user_input
    
    # If files are attached, always route to general agent for analysis
    if has_files:
        state["intent"] = "file_analysis"
        state["agent_type"] = "general_agent"
        state["extracted_slots"] = {}
        state["missing_slots"] = []
        print(f"Main Orchestrator: File attachment detected")
        print(f"Routing to: 'general_agent' for file analysis")
        return state
    
    # Build a prompt for the orchestrator to classify intent
    orchestrator_prompt = """You are the Main Orchestrator for a customer support AI system.

Your ONLY job is to analyze the user's message and determine which specialized agent should handle it.

Available Agents:
1. ORDER AGENT - Handles: order status, tracking, delivery, cancellation
2. PRODUCT AGENT - Handles: product information, price, availability, features, specifications
3. BILLING AGENT - Handles: invoices, payments, refunds, billing questions
4. ACCOUNT AGENT - Handles: email, password, username, account profile, login issues
5. GENERAL AGENT - Handles: general questions, FAQ, greetings, chitchat, anything else

Analyze the user's message and respond with ONLY the agent type that should handle this request.

Respond with exactly one of these:
- order_agent
- product_agent
- billing_agent
- account_agent
- general_agent

Examples:
User: "Where is my order?" → order_agent
User: "How much does the laptop cost?" → product_agent
User: "I need a refund" → billing_agent
User: "I forgot my password" → account_agent
User: "Hello, how are you?" → general_agent
User: "What can you help me with?" → general_agent
User: "Tell me a joke" → general_agent

Do not provide any explanation. Just respond with the agent name.
"""
    
    # Use LLM to classify intent
    agent_classification = generate(
        text=user_input,
        conversation_history=conversation_history[-5:] if conversation_history else [],
        system_prompt=orchestrator_prompt
    )
    
    # Clean up the response
    agent_classification = agent_classification.strip().lower()
    
    # Validate and extract agent type
    if "order" in agent_classification:
        agent_type = "order_agent"
        intent = "order_inquiry"
    elif "product" in agent_classification:
        agent_type = "product_agent"
        intent = "product_inquiry"
    elif "billing" in agent_classification:
        agent_type = "billing_agent"
        intent = "billing_inquiry"
    elif "account" in agent_classification:
        agent_type = "account_agent"
        intent = "account_inquiry"
    elif "general" in agent_classification:
        agent_type = "general_agent"
        intent = "general_inquiry"
    else:
        # Default to general agent for unclear cases
        agent_type = "general_agent"
        intent = "general_inquiry"
    
    # Update state with routing information
    state["intent"] = intent
    state["agent_type"] = agent_type
    state["extracted_slots"] = {}
    state["missing_slots"] = []
    
    print(f"Main Orchestrator: User message received")
    print(f"Intent detected: '{intent}'")
    print(f"Routing to: '{agent_type}'")
    
    return state


def route_to_agent(state: Dict) -> str:
    """
    Conditional edge function for LangGraph.
    
    Returns the name of the specialized agent node that should handle this request.
    This is used by LangGraph to determine the next node in the graph.
    
    Args:
        state: Current conversation state with agent_type set
    
    Returns:
        Agent node name (order_agent, product_agent, billing_agent, account_agent, or general_agent)
    """
    agent_type = state.get("agent_type", "general_agent")
    return agent_type
