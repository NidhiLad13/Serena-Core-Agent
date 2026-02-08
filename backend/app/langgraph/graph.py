# app/langgraph/graph.py
"""
Multi-agent orchestration graph using LangGraph.

Flow:
1. User sends message
2. Main Orchestrator analyzes intent
3. Routes to appropriate specialized agent
4. Agent uses its tools with dummy data
5. Agent returns response
6. Response sent back to user
"""
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    classify_intent,
    route_to_agent,
    order_agent,
    product_agent,
    billing_agent,
    account_agent,
    general_agent
)
from app.services.langgraph_checkpoint import langgraph_checkpoint

# Create multi-agent graph
graph = StateGraph(AgentState)

# Add Main Orchestrator (Router) - Entry point for all messages
graph.add_node("router", classify_intent)

# Add 5 Specialized Agent nodes
graph.add_node("order_agent", order_agent)
graph.add_node("product_agent", product_agent)
graph.add_node("billing_agent", billing_agent)
graph.add_node("account_agent", account_agent)
graph.add_node("general_agent", general_agent)

# Set entry point - all conversations start with the Main Orchestrator
graph.set_entry_point("router")

# Add conditional edges from router to specialized agents
# The router analyzes intent and routes to the appropriate agent
graph.add_conditional_edges(
    "router",
    route_to_agent,
    {
        "order_agent": "order_agent",
        "product_agent": "product_agent",
        "billing_agent": "billing_agent",
        "account_agent": "account_agent",
        "general_agent": "general_agent",
    }
)

# All specialized agents complete and return to END
graph.add_edge("order_agent", END)
graph.add_edge("product_agent", END)
graph.add_edge("billing_agent", END)
graph.add_edge("account_agent", END)
graph.add_edge("general_agent", END)

# Compile with MongoDB checkpointer for state persistence
checkpointer = langgraph_checkpoint.get_checkpointer()

if checkpointer:
    agent_graph = graph.compile(checkpointer=checkpointer)
    print("Multi-agent system compiled with MongoDB checkpointer")
    print("Main Orchestrator: Router")
    print("Specialized Agents: Order, Product, Billing, Account, General")
else:
    agent_graph = graph.compile()
    print("Multi-agent system compiled WITHOUT checkpointer (fallback mode)")
    print("Main Orchestrator: Router")
    print("Specialized Agents: Order, Product, Billing, Account, General")
