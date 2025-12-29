from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field("2.0", pattern=r"^2\.0$")
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = Field("2.0", pattern=r"^2\.0$")
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class ToolInputSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None

class ToolDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    inputSchema: ToolInputSchema

class ToolListResult(BaseModel):
    tools: List[ToolDefinition]

class TextContent(BaseModel):
    type: str = "text"
    text: str

class ToolCallResult(BaseModel):
    content: List[TextContent]
    isError: Optional[bool] = False
