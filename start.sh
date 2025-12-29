#!/bin/sh

# 获取脚本所在的绝对路径
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

sed_inplace() {
    expr="$1"
    file="$2"
    if sed --version >/dev/null 2>&1; then
        sed -i "$expr" "$file"
    else
        sed -i '' "$expr" "$file"
    fi
}

# 检查虚拟环境的配置文件中的路径是否与当前路径一致
if [ -f "$SCRIPT_DIR/venv/pyvenv.cfg" ]; then
    # 从pyvenv.cfg中提取原始路径
    ORIGINAL_PATH=$(grep "command" "$SCRIPT_DIR/venv/pyvenv.cfg" | awk -F" " '{print $NF}')
    VENV_DIR=$(dirname "$ORIGINAL_PATH")
    
    # 如果原始路径与当前路径不同，则更新所有相关文件中的路径
    if [ "$VENV_DIR" != "$SCRIPT_DIR" ]; then
        echo "检测到路径变更，从 $VENV_DIR 到 $SCRIPT_DIR"
        echo "更新虚拟环境路径..."
        
        # 更新虚拟环境中的路径引用
        grep -rl "$VENV_DIR" "$SCRIPT_DIR/venv/bin" 2>/dev/null | while IFS= read -r file; do
            sed_inplace "s|$VENV_DIR|$SCRIPT_DIR|g" "$file"
        done
        
        # 更新pyvenv.cfg文件
        sed_inplace "s|$VENV_DIR|$SCRIPT_DIR|g" "$SCRIPT_DIR/venv/pyvenv.cfg"
        
        echo "虚拟环境路径已更新"
    fi
fi

# Activate virtual environment using absolute path
. "$SCRIPT_DIR/venv/bin/activate"

# Install missing packages if requirements.txt exists
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

# 从配置文件中获取服务器端口号
PORT=$(grep -A 2 '"server"' "$SCRIPT_DIR/config.json" | grep '"port"' | grep -o '[0-9]\+')
if [ -z "$PORT" ]; then
    # 如果无法从配置文件获取端口，使用默认端口8008
    PORT=8008
    echo "无法从配置文件获取服务器端口号，使用默认端口: $PORT"
else
    echo "从配置文件获取到服务器端口号: $PORT"
fi

# 查找并终止使用该端口的进程
PIDS=$(lsof -t -i:$PORT)


if [ ! -z "$PIDS" ]; then
    echo "Killing existing processes: $PIDS"
    for PID in $PIDS; do
        kill $PID
    done
    sleep 2  # Wait for processes to terminate
fi

# Start the server in background
cd "$SCRIPT_DIR"  # 切换到脚本目录
export PYTHONPATH=$SCRIPT_DIR:$PYTHONPATH
nohup "$SCRIPT_DIR/venv/bin/python" -m app.main > "$SCRIPT_DIR/server.log" 2>&1 &
echo "Server started with PID $!"
echo "日志文件: $SCRIPT_DIR/server.log"
