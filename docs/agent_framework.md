# Module 2: Agent Framework

This module implements the core reasoning and execution loop of the AI Desktop Assistant using LangGraph.

## Design Decisions

1. **State Management (`backend/agent/state.py`)**: Uses LangGraph's `MessagesState` as the foundation, extending it with custom fields: `current_plan`, `retry_count`, and `reflection`. This allows the agent to maintain short-term memory, reason over tool failures, and prevent infinite loops.
2. **LLM Pluggability (`backend/agent/llm.py`)**: The system defaults to Ollama (via `langchain-ollama`) for local, private execution as specified in the master prompt. However, by using a factory function and Pydantic settings, we can trivially swap to OpenAI or Anthropic by changing the `LLM_PROVIDER` setting.
3. **Tool Execution Node (`backend/agent/nodes.py`)**: Instead of relying entirely on LangChain's prebuilt `ToolNode`, we implement a custom `tool_execution_node`. This guarantees that all LLM tool calls must pass through our `ToolRegistry` and `PermissionManager`, honoring the safety and validation contracts established in Module 1.
4. **Reflection Loop (`backend/agent/graph.py`)**: The graph is designed with conditional edges. If a tool fails (e.g., returns an error or is denied permission), the graph routes to a `reflection` node. The agent receives the error and can retry with different arguments. A `retry_count` limits this loop to prevent the agent from getting stuck.

## File Structure

```text
backend/agent/
├── graph.py       # Assembles the StateGraph and conditional edges
├── llm.py         # LLM factory (Ollama, OpenAI, Anthropic)
├── nodes.py       # Reasoning, tool execution, and reflection logic
└── state.py       # AgentState definition
```

## Setup & Usage

Ensure dependencies are installed:
```powershell
pip install -r requirements.txt
```

To run the interactive verification script:
```powershell
python run_agent.py
```
*(Note: If you do not have Ollama running locally, the LLM will fail to connect, but the graph structure will still be instantiated.)*

## Testing

A complete pytest suite is provided in `tests/test_agent.py`. These tests use `unittest.mock` to mock the LLM responses, ensuring that the graph routing, tool execution, and reflection loops can be verified without needing a live LLM or network connection.

To run the tests:
```powershell
pytest tests/test_agent.py
```

## Known Limitations / TODOs

- **Memory Optimization**: Currently, the entire conversation history is maintained in `messages`. For long-running tasks, we will need to implement a memory summarization node (planned for Module 4).
- **Task Decomposition**: The `current_plan` state field is defined but not yet actively utilized by a dedicated planning node. This will be integrated when the Workflow Engine (Module 7) is built.
