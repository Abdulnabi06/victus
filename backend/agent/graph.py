import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from backend.agent.state import AgentState
from backend.agent.nodes import reasoning_node, tool_execution_node, reflection_node

logger = logging.getLogger(__name__)

# Define conditional edges
def route_after_reasoning(state: AgentState) -> Literal["tools", "end"]:
    """Routes to tools if reasoning produced a tool call, else ends."""
    messages = state.get("messages", [])
    if not messages:
        return "end"
        
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"

def route_after_tools(state: AgentState) -> Literal["reflection", "reasoning"]:
    """Routes to reflection if tools failed and retry count is within limit, else loops back to reasoning."""
    retry_count = state.get("retry_count", 0)
    
    # Simple logic: if retry_count > 0 it means there was an error in the last tool execution
    if retry_count > 0:
        if retry_count > 3:
            logger.warning("Max retries exceeded for tool execution.")
            return "reasoning" # Let the LLM see the final error and hopefully stop
        return "reflection"
        
    return "reasoning"

def create_agent_graph():
    """
    Assembles the state graph for the agent.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("reflection", reflection_node)
    
    # Add edges
    workflow.set_entry_point("reasoning")
    
    workflow.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "reflection": "reflection",
            "reasoning": "reasoning"
        }
    )
    
    workflow.add_edge("reflection", "reasoning")
    
    return workflow.compile()

# Global graph instance
agent_graph = create_agent_graph()
