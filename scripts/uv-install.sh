#!/bin/bash
# UV 方式安装/同步依赖

set -e

cd "$(dirname "$0")/.."

echo "📦 同步依赖 (使用 uv.lock)..."
uv sync --frozen

echo ""
echo "✅ 依赖已同步"
echo "虚拟环境位置: .venv/"
echo ""
echo "运行方式:"
echo "  ./scripts/uv-run.sh python -m video2markdown.cli --help"
echo "  ./scripts/uv-test.sh tests/unit/ -v"
