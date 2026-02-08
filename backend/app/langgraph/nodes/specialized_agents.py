"""
Specialized agent nodes for the multi-agent orchestration system.

Each agent is an expert in handling a specific domain:
- Order Agent: Order status, tracking, delivery, cancellation
- Product Agent: Product info, availability, pricing, specifications
- Billing Agent: Invoices, payments, refunds
- Account Agent: Email, password, username, profile management
"""
from typing import Dict, List
from app.services.llm_agent import generate_with_agent
from app.services.llm_gemini import generate
from app.config.agent_config import get_agent_config
from pathlib import Path
import re

# Load agent prompts
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "agents"


def extract_entities_from_history(conversation_history: List[Dict], agent_type: str) -> Dict:
    """
    Extract key entities from conversation history automatically.
    This helps agents find information without asking again.
    
    Args:
        conversation_history: List of conversation messages
        agent_type: Type of agent (order_agent, product_agent, etc.)
    
    Returns:
        Dictionary of extracted entities
    """
    entities = {}
    
    # Combine all messages into searchable text
    all_text = " ".join([msg.get("content", "") for msg in conversation_history])
    
    # Extract email addresses (for account_agent, billing_agent)
    if agent_type in ["account_agent", "billing_agent"]:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, all_text)
        if emails:
            entities["email"] = emails[-1]  # Use most recent email
    
    # Extract order IDs (for order_agent, billing_agent)
    if agent_type in ["order_agent", "billing_agent"]:
        order_pattern = r'ORD-\d+'
        orders = re.findall(order_pattern, all_text, re.IGNORECASE)
        if orders:
            entities["order_id"] = orders[-1].upper()  # Use most recent order ID
    
    # Extract invoice IDs (for billing_agent)
    if agent_type == "billing_agent":
        invoice_pattern = r'INV-\d+-\d+'
        invoices = re.findall(invoice_pattern, all_text, re.IGNORECASE)
        if invoices:
            entities["invoice_id"] = invoices[-1].upper()
    
    # Extract product names (for product_agent)
    if agent_type == "product_agent":
        # Look for common product patterns
        product_patterns = [
            r'Dell XPS \d+',
            r'MacBook (?:Pro|Air) \d+',
            r'iPhone \d+',
            r'Samsung Galaxy \w+',
            r'ThinkPad \w+',
            # Add more patterns as needed
        ]
        for pattern in product_patterns:
            products = re.findall(pattern, all_text, re.IGNORECASE)
            if products:
                entities["product_name"] = products[-1]
                break
    
    return entities


def load_agent_prompt(agent_name: str) -> str:
    """Load prompt template for a specialized agent."""
    prompt_file = PROMPTS_DIR / f"{agent_name}.txt"
    if prompt_file.exists():
        return prompt_file.read_text()
    else:
        print(f"Warning: Prompt file not found: {prompt_file}")
        return f"You are a customer support agent specializing in {agent_name.replace('_', ' ')}."


def format_agent_prompt(template: str, collected_fields: Dict, missing_fields: list) -> str:
    """
    Format agent prompt with current slot information.
    
    Args:
        template: The agent's prompt template with placeholders
        collected_fields: Dictionary of already collected field values
        missing_fields: List of fields still needed
    
    Returns:
        Formatted prompt with slot information injected
    """
    # Format collected fields with explicit tool instructions
    if collected_fields:
        fields_str = "\n".join([f"- {k}: {v}" for k, v in collected_fields.items()])
        fields_str += "\n\n🔥 IMPORTANT: These values were ALREADY PROVIDED by the user. USE THEM IMMEDIATELY with your tools!"
        
        # Add specific tool call suggestions based on what we have
        if "email" in collected_fields:
            fields_str += f"\n→ You can call tools with email=\"{collected_fields['email']}\""
        if "order_id" in collected_fields:
            fields_str += f"\n→ You can call tools with order_id=\"{collected_fields['order_id']}\""
        if "product_name" in collected_fields:
            fields_str += f"\n→ You can call tools with product_name=\"{collected_fields['product_name']}\""
        if "invoice_id" in collected_fields:
            fields_str += f"\n→ You can call tools with invoice_id=\"{collected_fields['invoice_id']}\""
    else:
        fields_str = "None yet (user just started the conversation)"
    
    # Format missing fields
    if missing_fields:
        missing_str = "\n".join([f"- {field}" for field in missing_fields])
    else:
        missing_str = "All required fields have been collected!"
    
    return template.format(
        collected_fields=fields_str,
        missing_fields=missing_str
    )


async def order_agent(state: Dict) -> Dict:
    """
    Order Agent - Handles all order-related inquiries.
    
    Responsibilities:
    - Order status checks
    - Tracking information
    - Delivery estimates
    - Order cancellations
    
    Tools: get_order_status, get_tracking_info, cancel_order
    """
    return await _run_specialized_agent(state, "order_agent")


async def product_agent(state: Dict) -> Dict:
    """
    Product Agent - Handles all product-related inquiries.
    
    Responsibilities:
    - Product information and features
    - Availability and stock checks
    - Pricing information
    - Product specifications
    
    Tools: get_product_info, check_product_availability, get_product_price
    """
    return await _run_specialized_agent(state, "product_agent")


async def billing_agent(state: Dict) -> Dict:
    """
    Billing Agent - Handles all billing and payment inquiries.
    
    Responsibilities:
    - Invoice retrieval
    - Payment status checks
    - Refund requests
    - Billing questions
    
    Tools: get_invoice, get_payment_status, request_refund
    """
    return await _run_specialized_agent(state, "billing_agent")


async def account_agent(state: Dict) -> Dict:
    """
    Account Agent - Handles all account-related inquiries.
    
    Responsibilities:
    - Account information retrieval
    - Email updates
    - Username changes
    - Password resets
    - Profile management
    
    Tools: get_account_info, update_account_email, update_account_username, reset_password
    """
    return await _run_specialized_agent(state, "account_agent")


async def general_agent(state: Dict) -> Dict:
    """
    General Agent - Handles general inquiries, FAQ, and file analysis.
    
    Responsibilities:
    - Answer general questions
    - Analyze attached documents (PDF, Word, text files)
    - Analyze attached images
    - Handle FAQ and miscellaneous queries
    - Provide helpful information from file contents
    
    Tools: None (uses base LLM capabilities for general assistance)
    """
    return await _run_specialized_agent(state, "general_agent")


async def _run_specialized_agent(state: Dict, agent_name: str) -> Dict:
    """
    Generic function to run any specialized agent.
    
    This function:
    1. Extracts entities from conversation history automatically
    2. Loads the agent-specific prompt
    3. Injects current slot information (collected and missing fields)
    4. Adds semantic context from relevant past memories
    5. Generates a response using the agent's LLM with its specific tools
    6. Returns updated state with the response
    
    Args:
        state: Current conversation state
        agent_name: Name of the agent to run (e.g., "order_agent")
    
    Returns:
        Updated state with the agent's response
    """
    config = get_agent_config()
    user_input = state["user_input"]
    history = state.get("conversation_history", [])
    collected_fields = state.get("extracted_slots", {})
    missing_fields = state.get("missing_slots", [])
    semantic_context = state.get("semantic_context", [])
    
    # STEP 1: Automatically extract entities from conversation history
    auto_extracted = extract_entities_from_history(history, agent_name)
    
    # Merge with existing collected fields (auto-extracted takes precedence if newer)
    collected_fields = {**collected_fields, **auto_extracted}
    
    # Update state with extracted entities
    state["extracted_slots"] = collected_fields
    
    print(f"{agent_name}: Auto-extracted entities: {auto_extracted}")
    print(f"{agent_name}: User input length: {len(user_input)} chars")
    
    # Load and format agent-specific prompt
    template = load_agent_prompt(agent_name)
    system_prompt = format_agent_prompt(template, collected_fields, missing_fields)
    
    # Add semantic context if available (relevant past memories)
    if semantic_context:
        context_str = "\n\nRELEVANT CONTEXT FROM EARLIER IN CONVERSATION:\n"
        for i, mem in enumerate(semantic_context[:3], 1):  # Top 3 most relevant
            context_str += f"{i}. {mem['sender']}: {mem['text']}\n"
        context_str += "\nUse this context to avoid asking for information the user already provided.\n"
        system_prompt += context_str
    
    # Generate response - use simple LLM for general_agent (no tools), otherwise use agent with tools
    if agent_name == "general_agent":
        # General agent doesn't use tools, just base LLM capabilities
        response = generate(
            text=user_input,
            conversation_history=history[-config.get("conversation_history_limit", 10):],
            system_prompt=system_prompt
        )
    else:
        # Other specialized agents use tools
        response = generate_with_agent(
            agent_name=agent_name,
            text=user_input,
            conversation_history=history[-config.get("conversation_history_limit", 10):],
            system_prompt=system_prompt
        )
    
    state["response"] = response
    print(f"{agent_name} generated response (entities: {collected_fields}, semantic context: {len(semantic_context)} memories)")
    
    return state
