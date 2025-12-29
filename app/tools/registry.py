import inspect
from typing import Callable, Dict, Any, Optional
from app.core.mcp_types import ToolDefinition, ToolInputSchema

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, input_schema: Dict[str, Any]):
        def decorator(func: Callable):
            self._tools[name] = func
            self._definitions[name] = ToolDefinition(
                name=name,
                description=description,
                inputSchema=ToolInputSchema(**input_schema)
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_definitions(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        func = self.get_tool(name)
        if not func:
            raise ValueError(f"Tool {name} not found")
        
        # Check if function is async
        if inspect.iscoroutinefunction(func):
            return await func(**arguments)
        else:
            return func(**arguments)

registry = ToolRegistry()
