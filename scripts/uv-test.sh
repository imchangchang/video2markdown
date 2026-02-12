#!/bin/bash
# UV 方式运行测试

set -e

cd "$(dirname "$0")/.."

echo "🧪 使用 uv 运行测试..."
uv run --frozen pytest "$@"
