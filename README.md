# MCP Hive Server

一个基于 Model Context Protocol (MCP) 的 Apache Hive 数据库查询服务器，提供 HTTP 接口用于执行 Hive SQL 查询。

## 项目路径变更说明

本项目支持在不同路径或服务器之间迁移，无需重新创建虚拟环境。当项目路径变更时，`start.sh` 脚本会自动检测并更新虚拟环境中的路径引用，确保服务能够正常启动。

### 自动路径检测机制

启动脚本会通过以下步骤自动处理路径变更：

1. 检测当前脚本所在的绝对路径
2. 读取虚拟环境配置文件 `pyvenv.cfg` 中记录的原始路径
3. 比较两个路径，如果不一致，则自动更新所有相关文件中的路径引用
4. 更新完成后，使用更新后的虚拟环境启动服务

### 迁移步骤

1. 将整个项目目录（包括 `venv` 文件夹）复制到新位置或新服务器
2. 运行 `./start.sh` 启动服务，脚本会自动检测路径变更并更新虚拟环境
3. 使用 `./stop.sh` 可以正常停止服务

无需重新创建虚拟环境或重新安装依赖，大大简化了部署和迁移过程。

### 进程管理机制

本项目使用基于端口的进程检测和管理机制，相比传统的进程名称检测方式，具有更高的兼容性和可靠性：

1. **端口检测**: 启动和停止脚本会自动从配置文件中读取服务器端口（默认8008），并使用 `lsof` 命令检测占用该端口的进程
2. **自动清理**: 启动前自动终止占用相同端口的进程，避免端口冲突
3. **备用机制**: 如果端口检测失败，会回退到基于进程名的检测方式，确保服务能够被正确管理
4. **优雅关闭**: 停止脚本会先尝试正常终止进程，如果失败再强制终止，确保资源被正确释放

## 架构概述

### 系统架构

```
┌─────────────────┐    HTTP/JSON-RPC    ┌─────────────────┐    PyHive    ┌─────────────────┐
│   MCP Client    │ ◄─────────────────► │  MCP Hive Server │ ◄──────────► │   HiveServer2   │
│  (Cline/IDE)    │                     │   (FastAPI)     │              │   (Apache Hive) │
└─────────────────┘                     └─────────────────┘              └─────────────────┘
```

### 核心组件

- **FastAPI 服务器**: 提供 HTTP 端点，处理 MCP 协议请求
- **PyHive 连接器**: 管理与 HiveServer2 的连接和查询执行
- **JSON-RPC 处理器**: 解析和响应 MCP 协议消息
- **流式响应支持**: 支持 Server-Sent Events (SSE) 用于实时数据传输

## 协议支持

### MCP (Model Context Protocol)

- **协议版本**: 2024-11-05
- **传输方式**: HTTP/HTTPS
- **消息格式**: JSON-RPC 2.0
- **流式支持**: Server-Sent Events (SSE)

### 支持的 MCP 方法

1. **initialize**: 初始化连接，返回服务器能力
2. **tools/list**: 获取可用工具列表
3. **tools/call**: 执行指定工具

## 工具功能

### query_hive 工具

执行 Hive SQL 查询的核心工具，支持：

- **查询类型**: 
  - `SHOW DATABASES` - 显示所有数据库
  - `SHOW TABLES` - 显示表列表
  - `SELECT` 语句 - 数据查询
  - `DESCRIBE` - 表结构查询
  - 其他标准 Hive SQL 语句

- **参数**:
  - `query` (必需): SQL 查询语句
  - `database` (可选): 指定数据库名称

- **返回格式**:
  ```json
  {
    "columns": ["列名1", "列名2"],
    "data": [["值1", "值2"], ["值3", "值4"]],
    "row_count": 2
  }
  ```

## 配置说明

### config.json 配置文件

```json
{
  "hive": {
    "host": "10.9.62.211",          // HiveServer2 主机地址
    "port": 10000,                   // HiveServer2 端口
    "username": "hive",              // 用户名
    "password": "hive123",           // 密码
    "database": "default",           // 默认数据库
    "auth": "LDAP",                  // 认证方式 (LDAP/PLAIN/KERBEROS)
    "configuration": {               // Hive 配置参数
      "hive.cli.print.header": "true"
    }
  },
  "allowed_origins": [               // CORS 允许的源
    "http://localhost:3000",
    "https://trusted.com"
  ],
  "server": {
    "host": "::",                    // 服务器监听地址 (:: 表示所有接口)
    "port": 8008                     // 服务器端口
  }
}
```

### 配置参数详解

#### Hive 连接配置
- `host`: HiveServer2 服务器地址
- `port`: HiveServer2 端口 (默认 10000)
- `username`: Hive 用户名
- `password`: Hive 密码 (可选)
- `database`: 默认连接的数据库
- `auth`: 认证方式
  - `PLAIN`: 明文认证
  - `LDAP`: LDAP 认证
  - `KERBEROS`: Kerberos 认证
- `configuration`: Hive 会话配置参数

#### 服务器配置
- `host`: 服务器绑定地址
  - `::`: 绑定所有 IPv6 和 IPv4 接口
  - `0.0.0.0`: 绑定所有 IPv4 接口
  - `127.0.0.1`: 仅本地访问
- `port`: HTTP 服务端口

#### 安全配置
- `allowed_origins`: CORS 允许的源列表，用于 Web 客户端访问控制

## 部署指南

### 环境要求

- Python 3.7+
- 网络访问 HiveServer2 服务
- 有效的 Hive 用户凭据

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd mcp-hiveserver2
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置服务**
   ```bash
   # 编辑 config.json 配置文件
   ```

4. **测试连接**
   ```bash
   python -c "from pyhive import hive; conn = hive.Connection(host='your-hive-host', port=10000, username='your-username')"
   ```

### Docker 部署 (可选)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8008

CMD ["python", "hiveservermcp.py"]
```

## 运行说明

### 启动服务器

```bash
# 推荐启动方式
sh start.sh

# 或直接运行
python hiveservermcp.py

# 或使用 uvicorn
uvicorn hiveservermcp:app --host 0.0.0.0 --port 8008

# 后台运行
nohup python hiveservermcp.py > server.log 2>&1 &
```

### 服务验证

1. **健康检查**
   ```bash
   curl http://localhost:8008/mcp
   ```

2. **获取工具列表**
   ```bash
   curl -X POST http://localhost:8008/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

3. **执行查询**
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

### 日志监控

服务器启动后会输出详细日志，包括：
- 连接状态
- 请求处理
- 查询执行
- 错误信息

```bash
# 实时查看日志
tail -f server.log

# 查看错误日志
grep ERROR server.log
```

## 客户端集成

### Cline MCP 配置

在 Cline 的 MCP 设置中添加：

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

### 编程接口

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

# 使用示例
result = query_hive("SHOW DATABASES")
print(result)
```

## 故障排除

### 常见问题

1. **连接失败**
   - 检查 HiveServer2 服务状态
   - 验证网络连通性
   - 确认用户凭据正确

2. **认证错误**
   - 检查 `auth` 配置是否正确
   - 验证用户名密码
   - 确认 LDAP/Kerberos 配置

3. **查询超时**
   - 检查查询复杂度
   - 增加连接超时设置
   - 优化 SQL 语句

4. **CORS 错误**
   - 添加客户端域名到 `allowed_origins`
   - 检查请求头设置

### 调试模式

```bash
# 启用详细日志
export PYTHONPATH=.
export LOG_LEVEL=DEBUG
python hiveservermcp.py
```

## 安全注意事项

1. **网络安全**
   - 使用 HTTPS 传输敏感数据
   - 限制服务器访问 IP 范围
   - 配置防火墙规则

2. **认证安全**
   - 使用强密码
   - 定期更换凭据
   - 启用 Kerberos 认证（推荐）

3. **配置安全**
   - 保护 config.json 文件权限
   - 不要在代码中硬编码密码
   - 使用环境变量存储敏感信息

## 性能优化

1. **连接池**
   - 当前使用临时连接，可考虑实现连接池
   - 减少连接建立开销

2. **查询优化**
   - 使用 LIMIT 限制结果集大小
   - 避免全表扫描
   - 合理使用分区

3. **缓存策略**
   - 缓存元数据查询结果
   - 实现查询结果缓存

## 许可证

[添加适当的许可证信息]

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 支持

如有问题或建议，请：
- 提交 Issue
- 发送邮件至 [维护者邮箱]
- 查看项目 Wiki

---

客户端配置（cherry Studio，Cline 可行）
{
  "mcpServers": {
    "mcp-hiveserver2": {
      "url": "http://localhost:8008/mcp"
    }
  }
}



**版本**: 1.0.0  
**最后更新**: 2025-07-22

