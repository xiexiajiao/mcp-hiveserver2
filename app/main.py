import json
import logging
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.tools.registry import registry
# Import tools to register them
import app.tools.hive_tools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.core.session import session_manager

app = FastAPI(title="Hive MCP Server")

# CORS Middleware
origins = config.allowed_origins or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _origin_allowed(origin):
    if not config.allowed_origins:
        return True
    if not origin:
        return True
    return origin in config.allowed_origins

@app.on_event("startup")
async def startup_event():
    logger.info(json.dumps({"event": "config_loaded", "config": config.mask_secrets()}, ensure_ascii=False))

# SSE Endpoint for standard MCP clients
@app.get("/sse")
async def handle_sse(request: Request):
    """Standard MCP SSE endpoint"""
    session_id, queue = session_manager.create_session()
    logger.info(f"New SSE session created: {session_id}")
    
    async def event_generator():
        # Send endpoint event pointing to the message handler
        yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
        
        try:
            while True:
                # Wait for messages with timeout to send keepalive
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE session cancelled: {session_id}")
            session_manager.remove_session(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/messages")
async def handle_messages(request: Request):
    """Standard MCP POST endpoint for messages"""
    session_id = request.query_params.get("session_id")
    
    if not session_id or not session_manager.get_session(session_id):
        return Response(status_code=404, content="Session not found")

    try:
        body = await request.body()
        rpc_message = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)
        
    # Execute RPC request
    result = await handle_rpc_request(rpc_message)
    
    response = {
        "jsonrpc": "2.0",
        "result": result,
        "id": rpc_message.get('id')
    }
    
    queue = session_manager.get_session(session_id)
    if queue:
        await queue.put(response)
    
    return Response(status_code=202)

class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        error = {"code": self.code, "message": self.message}
        if self.data:
            error["data"] = self.data
        return error

@app.post("/mcp")
async def mcp_post(request: Request):
    """HTTP POST endpoint for MCP protocol"""
    origin = request.headers.get("origin")
    if not _origin_allowed(origin):
        return Response(status_code=403)
    
    try:
        body = await request.body()
        rpc_message = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    if 'method' in rpc_message:
        request_id = rpc_message.get('id')
        try:
            result = await handle_rpc_request(rpc_message)
            
            # If it's a notification (no id), return 202 Accepted and no content
            if request_id is None:
                return Response(status_code=202)
                
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            return JSONResponse(content=response)
        except JsonRpcError as e:
            # If it's a notification, don't return error unless critical? 
            # Standard says no response to notifications even on error, unless it's ParseError (handled above)
            if request_id is None:
                return Response(status_code=202)

            response = {
                "jsonrpc": "2.0",
                "error": e.to_dict(),
                "id": request_id
            }
            return JSONResponse(content=response)
        except Exception as e:
            if request_id is None:
                return Response(status_code=202)
                
            logger.error(f"Internal error: {e}")
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error", "data": str(e)},
                "id": request_id
            }
            return JSONResponse(content=response)
    else:
        return Response(status_code=202)

@app.get("/mcp")
async def mcp_get(request: Request):
    """MCP endpoint supporting SSE for clients connecting to /mcp"""
    origin = request.headers.get("origin")
    if not _origin_allowed(origin):
        return Response(status_code=403)
    
    # Check for SSE request
    accept_header = request.headers.get('accept', '')
    if 'text/event-stream' in accept_header:
        # Create a session and start streaming
        session_id, queue = session_manager.create_session()
        logger.info(f"New SSE session created on /mcp: {session_id}")
        
        async def event_generator():
            yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
            
            try:
                while True:
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            except asyncio.CancelledError:
                logger.info(f"SSE session cancelled: {session_id}")
                session_manager.remove_session(session_id)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        return Response(status_code=200, content="MCP Server Running")

@app.get("/")
async def root():
    return {"status": "online", "service": "Hive MCP Server"}

async def handle_rpc_request(rpc):
    # Remove try/catch here to let exceptions propagate to mcp_post
    method = rpc.get('method')
    params = rpc.get('params', {})
    
    if method == 'initialize':
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {}
            },
            'serverInfo': {
                'name': 'Hive MCP Server',
                'version': '1.0.0'
            }
        }
    elif method == 'notifications/initialized':
        # Client initialized, no response needed (handled by mcp_post as notification)
        return None
    elif method == 'ping':
        return {}
    elif method == 'tools/list':
        return {
            'tools': [t.model_dump() for t in registry.get_definitions()]
        }
    elif method == 'tools/call':
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        try:
            return await registry.call_tool(tool_name, arguments)
        except ValueError:
             return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps({"error": "Unknown tool"}, ensure_ascii=False)
                }],
                'isError': True
            }
        except Exception as e:
            return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps({"error": str(e)}, ensure_ascii=False)
                }],
                'isError': True
            }
    else:
        raise JsonRpcError(-32601, "Method not found")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Access: {request.method} {request.url} from {request.client.host}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Check connection on startup
    try:
        from app.core.hive_client import get_hive_connection
        conn = get_hive_connection()
        conn.cursor()
        conn.close()
        logger.info("HiveServer connection test successful.")
    except Exception as e:
        logger.error(f"HiveServer connection test failed: {e}")

    host = config.server.host
    port = config.server.port
    
    # Attempt to bind Dual Stack Socket (IPv4 + IPv6)
    sock = None
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Disable IPV6_V6ONLY to allow IPv4 connections on IPv6 socket (Dual Stack)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(('::', port))
        sock.listen(1000)
        logger.info(f"Successfully bound to Dual Stack socket (IPv4+IPv6) on port {port}")
    except Exception as e:
        logger.warning(f"Dual Stack binding failed: {e}. Falling back to configured host/port.")
        if sock:
            sock.close()
        sock = None

    if sock:
        # Run with the pre-opened dual-stack socket
        uvicorn.run(app, fd=sock.fileno())
    else:
        # Fallback to standard binding
        if host == '::':
             host = '0.0.0.0' # Fallback for safety if :: failed
        uvicorn.run(app, host=host, port=port)
