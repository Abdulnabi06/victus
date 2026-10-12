import json
import logging
from typing import Dict, Any, List

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
from backend.agent.state import AgentState
from backend.agent.llm import get_llm
from backend.tools.registry import registry
from backend.tools.permission import permission_manager

logger = logging.getLogger(__name__)

# System prompt for the agent
SYSTEM_PROMPT = """You are a Principal AI Desktop Assistant.
Your job is to understand the user's intent, formulate a plan, and execute it using the tools available to you.
If a tool requires permission, it will be handled by the system.
If a tool fails, reflect on the error and try a different approach or fix the parameters.
"""

def _convert_registry_tools_to_langchain():
    """Converts the internal ToolRegistry tools into LangChain tool schemas for binding."""
    tools = []
    for tool in registry.list_tools():
        schema = tool.args_schema.model_json_schema()
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": schema
            }
        })
    return tools

def reasoning_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the current state and decides the next action (tool call or final response).
    """
    logger.info("Executing reasoning_node")
    llm = get_llm()
    
    # Bind tools if we have any registered
    lc_tools = _convert_registry_tools_to_langchain()
    if lc_tools:
        llm = llm.bind_tools(lc_tools)
        
    messages = state.get("messages", [])
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    # Append reflection if present and not already handled
    reflection = state.get("reflection")
    if reflection:
        # We inject reflection as a temporary system message to guide the LLM
        messages.append(SystemMessage(content=f"Reflection on previous failure:\n{reflection}"))
    
    response = llm.invoke(messages)
    
    # Clear reflection and reset retry count on successful reasoning
    return {
        "messages": [response],
        "reflection": None,
        "retry_count": 0
    }

def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Intercepts tool calls, invokes the ToolRegistry, handles PermissionManager checks,
    and returns ToolMessages.
    """
    logger.info("Executing tool_execution_node")
    last_message = state["messages"][-1]
    
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"messages": []}
    
    tool_messages = []
    has_errors = False
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        
        tool = registry.get_tool(tool_name)
        
        if not tool:
            error_msg = f"Tool '{tool_name}' not found in registry."
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id, status="error"))
            has_errors = True
            continue
            
        if tool.requires_permission:
            # Check permission
            details = json.dumps(tool_args, indent=2)
            if not permission_manager.check_permission(tool_name, details):
                error_msg = f"Permission denied for tool '{tool_name}'."
                tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id, status="error"))
                has_errors = True
                continue
                
        # Execute tool
        result = registry.execute(tool_name, **tool_args)
        
        if result.success:
            tool_messages.append(ToolMessage(content=result.output or "Success", tool_call_id=tool_call_id))
        else:
            error_msg = f"Tool execution failed: {result.error}"
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id, status="error"))
            has_errors = True

    return {
        "messages": tool_messages,
        # If there are errors, we increment retry count so the graph can route to reflection
        "retry_count": state.get("retry_count", 0) + (1 if has_errors else 0)
    }

def reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Reviews tool errors and generates a reflection to guide the next reasoning step.
    """
    logger.info("Executing reflection_node")
    last_message = state["messages"][-1]
    
    if not isinstance(last_message, ToolMessage):
        return {}
        
    if last_message.status == "error":
        reflection_msg = (
            f"The previous tool call failed with the following error: {last_message.content}. "
            "Please analyze why it failed and adjust your approach. "
            "Do not repeat the exact same tool call without modifying the arguments or state."
        )
        return {"reflection": reflection_msg}
        
    return {}
