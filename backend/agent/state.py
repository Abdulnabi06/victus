from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State dictionary for the LangGraph agent framework.
    Extends built-in messages with task decomposition and reflection logic.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Track the current high-level plan or active subtasks
    current_plan: Optional[str]
    
    # Number of times we've retried a failed tool or step
    retry_count: int
    
    # Store any reflections on previous failures to guide the next reasoning step
    reflection: Optional[str]
    
    # Store arbitrary structured output from reasoning, like tool choices
    # before they are converted into actual ToolMessages
    tool_calls: List[Dict[str, Any]]
