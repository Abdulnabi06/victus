import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from pydantic import BaseModel

from backend.agent.graph import agent_graph
from backend.agent.state import AgentState
from backend.tools.registry import registry, Tool, ToolResult

# Dummy Tool for testing
class DummyArgs(BaseModel):
    query: str

def dummy_handler(query: str):
    if query == "fail":
        raise ValueError("Simulated failure")
    return f"Result for {query}"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Register a dummy tool before each test
    dummy_tool = Tool(
        name="dummy_tool",
        description="A dummy tool for testing",
        args_schema=DummyArgs,
        handler=dummy_handler,
    )
    registry.register(dummy_tool)
    yield
    # Clear registry after each test
    registry._tools.clear()

def test_graph_reasoning_no_tools():
    """Test that the graph simply ends if the LLM doesn't call a tool."""
    with patch("backend.agent.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # LLM returns a simple AIMessage without tool_calls
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(content="Hello there!")
        
        initial_state = {"messages": [HumanMessage(content="Hi")]}
        
        # Run graph
        result = agent_graph.invoke(initial_state)
        
        assert len(result["messages"]) > 0
        assert result["messages"][-1].content == "Hello there!"
        assert result.get("retry_count", 0) == 0

def test_graph_tool_execution_success():
    """Test that the graph correctly executes a tool requested by the LLM."""
    with patch("backend.agent.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # LLM returns an AIMessage with a tool_call
        tool_call = {
            "name": "dummy_tool",
            "args": {"query": "success"},
            "id": "call_123"
        }
        
        # First invocation returns tool call, second returns final answer
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [
            AIMessage(content="", tool_calls=[tool_call]),
            AIMessage(content="Tool executed successfully.")
        ]
        
        initial_state = {"messages": [HumanMessage(content="Run dummy tool")]}
        
        # Run graph
        result = agent_graph.invoke(initial_state)
        
        # Check messages: Human -> System(Prompt) -> AI(ToolCall) -> ToolMessage -> AI(Final)
        messages = result["messages"]
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        
        assert len(tool_messages) == 1
        assert tool_messages[0].content == "Result for success"

def test_graph_tool_execution_failure_and_reflection():
    """Test that the graph handles tool failure, generates reflection, and retries/stops."""
    with patch("backend.agent.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        tool_call_fail = {
            "name": "dummy_tool",
            "args": {"query": "fail"},
            "id": "call_456"
        }
        
        # 1st invoke: calls tool (fails)
        # 2nd invoke (after reflection): returns apology/final answer
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [
            AIMessage(content="", tool_calls=[tool_call_fail]),
            AIMessage(content="I'm sorry, the tool failed.")
        ]
        
        initial_state = {"messages": [HumanMessage(content="Run dummy tool to fail")]}
        
        # Run graph
        result = agent_graph.invoke(initial_state)
        
        messages = result["messages"]
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        
        assert len(tool_messages) == 1
        assert tool_messages[0].status == "error"
        assert "Simulated failure" in tool_messages[0].content
        
        # The final AI message should acknowledge the failure
        assert messages[-1].content == "I'm sorry, the tool failed."
