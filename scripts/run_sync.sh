#!/bin/bash
#
# 小红书博主内容自动沉淀系统 - 运行脚本
#
# 使用方法:
#   ./scripts/run_sync.sh          # 正常模式（有浏览器界面）
#   ./scripts/run_sync.sh --test   # 测试模式（只同步第一个博主）
#   ./scripts/run_sync.sh --headless  # 无头模式（服务器环境）

set -e

# 切换到项目目录
cd "$(dirname "$0")/.."

# 激活虚拟环境
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "错误: 未找到虚拟环境，请先运行:"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 运行同步脚本
echo "开始运行小红书博主内容同步..."
echo ""

python main.py "$@"

echo ""
echo "同步完成!"
