#!/bin/bash
# UV 方式运行 Python 代码
# 使用项目虚拟环境，无需手动激活

set -e

cd "$(dirname "$0")/.."

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装"
    echo "安装方式: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 使用 uv run 运行（自动使用项目虚拟环境）
# --frozen: 使用 uv.lock 中的锁定版本，不更新依赖
echo "🐍 使用 uv 运行..."
uv run --frozen "$@"
