# MCP Hive Server

A Model Context Protocol (MCP) based Apache Hive database query server that provides an HTTP interface for executing Hive SQL queries.

[中文文档](README.md) | [English Documentation](README_EN.md)

## Project Path Change Instructions

This project supports migration between different paths or servers without recreating the virtual environment. When the project path changes, the `start.sh` script automatically detects and updates path references in the virtual environment, ensuring the service starts correctly.

### Automatic Path Detection Mechanism

The startup script handles path changes automatically through the following steps:

1. Detects the current absolute path of the script.
2. Reads the original path recorded in the virtual environment configuration file `pyvenv.cfg`.
3. Compares the two paths; if they differ, it automatically updates path references in all relevant files.
4. Once updated, starts the service using the updated virtual environment.

### Migration Steps

1. Copy the entire project directory (including the `venv` folder) to the new location or server.
2. Run `./start.sh` to start the service; the script will automatically detect path changes and update the virtual environment.
3. Use `./stop.sh` to stop the service normally.

No need to recreate the virtual environment or reinstall dependencies, greatly simplifying the deployment and migration process.

### Process Management Mechanism

This project uses a port-based process detection and management mechanism, which offers higher compatibility and reliability compared to traditional process name detection:

1. **Port Detection**: Startup and stop scripts automatically read the server port (default 8008) from the configuration file and use the `lsof` command to detect processes occupying that port.
2. **Auto Cleanup**: Automatically terminates processes occupying the same port before startup to avoid port conflicts.
3. **Fallback Mechanism**: If port detection fails, it falls back to process name-based detection to ensure the service is managed correctly.
4. **Graceful Shutdown**: The stop script attempts to terminate the process normally first; if that fails, it forces termination to ensure resources are released correctly.

## Architecture Overview

### System Architecture

```
┌─────────────────┐    HTTP/JSON-RPC    ┌─────────────────┐    PyHive    ┌─────────────────┐
│   MCP Client    │ ◄─────────────────► │  MCP Hive Server │ ◄──────────► │   HiveServer2   │
│  (Cline/IDE)    │                     │   (FastAPI)     │              │   (Apache Hive) │
└─────────────────┘                     └─────────────────┘              └─────────────────┘
```

### Core Components

- **FastAPI Server**: Provides HTTP endpoints to handle MCP protocol requests.
- **PyHive Connector**: Manages connections to HiveServer2 and query execution.
- **JSON-RPC Handler**: Parses and responds to MCP protocol messages.
- **Streaming Response Support**: Supports Server-Sent Events (SSE) for real-time data transmission.

## Protocol Support

### MCP (Model Context Protocol)

- **Protocol Version**: 2024-11-05
- **Transport**: HTTP/HTTPS
- **Message Format**: JSON-RPC 2.0
- **Streaming Support**: Server-Sent Events (SSE)

### Supported MCP Methods

1. **initialize**: Initializes the connection and returns server capabilities.
2. **tools/list**: Gets the list of available tools.
3. **tools/call**: Executes a specified tool.

## Tool Functionality

### query_hive Tool

The core tool for executing Hive SQL queries, supporting:

- **Query Types**:
  - `SHOW DATABASES` - Show all databases
  - `SHOW TABLES` - Show table list
  - `SELECT` statements - Data query
  - `DESCRIBE` - Table structure query
  - Other standard Hive SQL statements

- **Parameters**:
  - `query` (Required): SQL query statement
  - `database` (Optional): Specify database name

- **Return Format**:
  ```json
  {
    "columns": ["col1", "col2"],
    "data": [["val1", "val2"], ["val3", "val4"]],
    "row_count": 2
  }
  ```

## Configuration Instructions

### config.json Configuration File

```json
{
  "hive": {
    "host": "10.9.62.211",          // HiveServer2 Host Address
    "port": 10000,                   // HiveServer2 Port
    "username": "hive",              // Username
    "password": "hive123",           // Password
    "database": "default",           // Default Database
    "auth": "LDAP",                  // Authentication Method (LDAP/PLAIN/KERBEROS)
    "configuration": {               // Hive Configuration Parameters
      "hive.cli.print.header": "true"
    }
  },
  "allowed_origins": [               // CORS Allowed Origins
    "http://localhost:3000",
    "https://trusted.com"
  ],
  "server": {
    "host": "::",                    // Server Listen Address (:: means all interfaces)
    "port": 8008                     // Server Port
  }
}
```

### Configuration Parameters Detail

#### Hive Connection Configuration
- `host`: HiveServer2 server address
- `port`: HiveServer2 port (default 10000)
- `username`: Hive username
- `password`: Hive password (optional)
- `database`: Default database to connect to
- `auth`: Authentication method
  - `PLAIN`: Plain text authentication
  - `LDAP`: LDAP authentication
  - `KERBEROS`: Kerberos authentication
- `configuration`: Hive session configuration parameters

#### Server Configuration
- `host`: Server binding address
  - `::`: Bind to all IPv6 and IPv4 interfaces
  - `0.0.0.0`: Bind to all IPv4 interfaces
  - `127.0.0.1`: Local access only
- `port`: HTTP service port

#### Security Configuration
- `allowed_origins`: List of allowed origins for CORS, used for web client access control

## Deployment Guide

### Environment Requirements

- Python 3.7+
- Network access to HiveServer2 service
- Valid Hive user credentials

### Installation Steps

1. **Clone Project**
   ```bash
   git clone <repository-url>
   cd mcp-hiveserver2
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Service**
   ```bash
   # Edit config.json configuration file
   ```

4. **Test Connection**
   ```bash
   python -c "from pyhive import hive; conn = hive.Connection(host='your-hive-host', port=10000, username='your-username')"
   ```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8008

CMD ["python", "hiveservermcp.py"]
```

## Running Instructions

### Start Server

```bash
# Recommended start method
sh start.sh

# Or run directly
python hiveservermcp.py

# Or use uvicorn
uvicorn hiveservermcp:app --host 0.0.0.0 --port 8008

# Run in background
nohup python hiveservermcp.py > server.log 2>&1 &
```

### Service Verification

1. **Health Check**
   ```bash
   curl http://localhost:8008/mcp
   ```

2. **Get Tool List**
   ```bash
   curl -X POST http://localhost:8008/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

3. **Execute Query**
   ```bash
   curl -X POST http://localhost:8008/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "tools/call",
       "params": {
         "name": "query_hive",
         "arguments": {"query": "SHOW DATABASES"}
       },
       "id": 2
     }'
   ```

### Log Monitoring

Detailed logs are output after the server starts, including:
- Connection status
- Request processing
- Query execution
- Error information

```bash
# View real-time logs
tail -f server.log

# View error logs
grep ERROR server.log
```

## Client Integration

### Cline MCP Configuration

Add to Cline's MCP settings:

```json
{
  "mcpServers": {
    "hive-server": {
      "command": "curl",
      "args": ["-X", "POST", "http://localhost:8008/mcp"],
      "protocol": "http",
      "url": "http://localhost:8008/mcp"
    }
  }
}
```

### Programming Interface

```python
import requests

def query_hive(query):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "query_hive",
            "arguments": {"query": query}
        },
        "id": 1
    }
    
    response = requests.post(
        "http://localhost:8008/mcp",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()

# Usage example
result = query_hive("SHOW DATABASES")
print(result)
```

## Troubleshooting

### Common Issues

1. **Connection Failure**
   - Check HiveServer2 service status
   - Verify network connectivity
   - Confirm user credentials are correct

2. **Authentication Error**
   - Check if `auth` configuration is correct
   - Verify username and password
   - Confirm LDAP/Kerberos configuration

3. **Query Timeout**
   - Check query complexity
   - Increase connection timeout settings
   - Optimize SQL statements

4. **CORS Error**
   - Add client domain to `allowed_origins`
   - Check request header settings

### Debug Mode

```bash
# Enable detailed logging
export PYTHONPATH=.
export LOG_LEVEL=DEBUG
python hiveservermcp.py
```

## Security Considerations

1. **Network Security**
   - Use HTTPS for sensitive data transmission
   - Restrict server access IP range
   - Configure firewall rules

2. **Authentication Security**
   - Use strong passwords
   - Regularly change credentials
   - Enable Kerberos authentication (Recommended)

3. **Configuration Security**
   - Protect config.json file permissions
   - Do not hardcode passwords in code
   - Use environment variables to store sensitive information

## Performance Optimization

1. **Connection Pool**
   - Currently uses temporary connections; consider implementing a connection pool
   - Reduce connection establishment overhead

2. **Query Optimization**
   - Use LIMIT to restrict result set size
   - Avoid full table scans
   - Use partitions reasonably

3. **Caching Strategy**
   - Cache metadata query results
   - Implement query result caching

## License

[Add appropriate license information]

## Contribution Guide

1. Fork the project
2. Create a feature branch
3. Submit changes
4. Push to branch
5. Create a Pull Request

## Support

If you have questions or suggestions, please:
- Submit an Issue
- Send an email to [Maintainer Email]
- View Project Wiki

---

Client Configuration (Cherry Studio, Cline compatible)
{
  "mcpServers": {
    "mcp-hiveserver2": {
      "url": "http://localhost:8008/mcp"
    }
  }
}

**Version**: 1.0.0
**Last Updated**: 2025-07-22
