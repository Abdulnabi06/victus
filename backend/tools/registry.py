import time
import logging
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class ToolResult(BaseModel):
    """Uniform result structure for all tool executions."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    output: Optional[str] = None

class Tool:
    """Represents a governed tool with validation, timeouts, and standard results."""
    def __init__(
        self,
        name: str,
        description: str,
        args_schema: Type[BaseModel],
        handler: Callable[..., Any],
        requires_permission: bool = False
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.handler = handler
        self.requires_permission = requires_permission

    def run(self, **kwargs) -> ToolResult:
        try:
            validated_args = self.args_schema(**kwargs)
        except ValidationError as e:
            return ToolResult(success=False, error=f"Validation error: {e}")
            
        try:
            # Module 1 pattern: Tool execution
            # Note: timeouts and retries would be implemented here in a full version.
            start_time = time.time()
            result = self.handler(**validated_args.model_dump())
            duration = time.time() - start_time
            logger.debug(f"Tool {self.name} executed in {duration:.2f}s")
            
            return ToolResult(success=True, data=result, output=str(result))
        except Exception as e:
            logger.error(f"Error in tool {self.name}: {e}")
            return ToolResult(success=False, error=str(e))

class ToolRegistry:
    """Registry for all available tools."""
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool {name} not found.")
        return tool.run(**kwargs)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

# Global registry
registry = ToolRegistry()
