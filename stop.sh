#!/bin/bash

# 获取脚本所在的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 从配置文件中获取服务器端口号
PORT=$(grep -A 2 '"server"' "$SCRIPT_DIR/config.json" | grep '"port"' | grep -o '[0-9]\+')
if [ -z "$PORT" ]; then
    # 如果无法从配置文件获取端口，使用默认端口8008
    PORT=8008
    echo "无法从配置文件获取服务器端口号，使用默认端口: $PORT"
else
    echo "从配置文件获取到服务器端口号: $PORT"
fi

# 查找使用该端口的进程
PIDS=$(lsof -t -i:$PORT)

# 如果没有找到进程，尝试使用进程名查找（作为备用方法）
if [ -z "$PIDS" ]; then
    echo "未找到使用端口 $PORT 的进程，尝试使用进程名查找..."
    # 查找运行app.main的进程
    PIDS=$(pgrep -f "python.*app.main")
    
    # 如果仍然没有找到进程
    if [ -z "$PIDS" ]; then
        echo "未找到运行中的服务器进程"
        exit 0
    fi
fi

# 移除重复的PID
PIDS=$(echo "$PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs)

if [ -z "$PIDS" ]; then
    echo "No running processes found for app.main"
    exit 0
fi

echo "Found running processes: $PIDS"

# Kill processes gracefully first
for PID in $PIDS; do
    echo "Stopping process $PID..."
    kill $PID
done

# Wait for processes to terminate
sleep 3

# 检查是否还有进程在使用该端口
REMAINING_PIDS=$(lsof -t -i:$PORT)

# 移除重复的PID
if [ ! -z "$REMAINING_PIDS" ]; then
    REMAINING_PIDS=$(echo "$REMAINING_PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs)
fi

if [ ! -z "$REMAINING_PIDS" ]; then
    echo "Some processes are still running, force killing: $REMAINING_PIDS"
    for PID in $REMAINING_PIDS; do
        echo "Force killing process $PID..."
        kill -9 $PID
    done
    sleep 1
fi

# 最终检查是否还有进程在使用该端口
FINAL_CHECK=$(lsof -t -i:$PORT)

# 如果端口检查没有发现进程，但我们仍然怀疑可能有进程在运行，使用进程名进行备用检查
if [ -z "$FINAL_CHECK" ]; then
    # 使用进程名进行备用检查
    FINAL_CHECK=$(pgrep -f "python.*app.main")
fi

# 移除重复的PID
if [ ! -z "$FINAL_CHECK" ]; then
    FINAL_CHECK=$(echo "$FINAL_CHECK" | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs)
fi
if [ -z "$FINAL_CHECK" ]; then
    echo "All processes stopped successfully"
else
    echo "Warning: Some processes may still be running: $FINAL_CHECK"
fi