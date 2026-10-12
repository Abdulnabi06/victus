import asyncio
from langchain_core.messages import HumanMessage
from backend.agent.graph import agent_graph
from backend.tools.registry import registry, Tool
from pydantic import BaseModel

class CalculatorArgs(BaseModel):
    expression: str

def calculator_handler(expression: str):
    """Simple calculator for demonstration."""
    try:
        # DO NOT use eval in production like this without safety checks.
        # This is strictly for demonstration of tool calling.
        return eval(expression, {"__builtins__": {}})
    except Exception as e:
        raise ValueError(f"Failed to evaluate expression: {e}")

def main():
    print("Initializing Agent Framework Module 2...")
    
    # Register a sample tool
    calc_tool = Tool(
        name="calculator",
        description="Evaluate a mathematical expression. Useful for doing math.",
        args_schema=CalculatorArgs,
        handler=calculator_handler,
    )
    registry.register(calc_tool)
    
    print("Registered tools:", [t.name for t in registry.list_tools()])
    print("Type your message (or 'quit' to exit):")
    
    # Initialize state
    state = {"messages": []}
    
    while True:
        try:
            user_input = input("\nUser> ")
            if user_input.lower() in ['quit', 'exit']:
                break
                
            state["messages"].append(HumanMessage(content=user_input))
            
            # Stream the graph execution
            print("\nAgent:")
            for event in agent_graph.stream(state):
                for k, v in event.items():
                    if "messages" in v and v["messages"]:
                        last_message = v["messages"][-1]
                        if hasattr(last_message, "content") and last_message.content:
                            print(f"[{k}] {last_message.content}")
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            print(f"[{k}] Calling tools: {[tc['name'] for tc in last_message.tool_calls]}")
                            
            # Update state for next iteration (simple memory)
            state = event[list(event.keys())[0]] # Get the final state from the last node
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
