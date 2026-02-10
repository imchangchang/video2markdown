# 贡献指南

感谢您对 Video2Markdown 项目的关注！本文档将帮助您快速开始贡献代码。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone <repository-url>
cd video_process
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key
```

## 代码规范

### Python 代码风格

- 使用 **Black** 进行代码格式化
- 使用 **Ruff** 进行代码检查
- 行长度限制：100 字符

```bash
# 格式化代码
black src/ tests/

# 代码检查
ruff check src/ tests/

# 自动修复
ruff check --fix src/ tests/
```

### 类型注解

- 所有函数参数和返回值都应添加类型注解
- 使用 `from __future__ import annotations` 支持延迟类型评估

```python
def process_video(video_path: Path, options: dict[str, Any]) -> ProcessingResult:
    ...
```

### 文档字符串

- 使用 Google 风格的文档字符串
- 为所有公共函数和类添加文档字符串

```python
def analyze_image(image_path: Path) -> str:
    """分析图片内容。
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        图片内容的文字描述
        
    Raises:
        FileNotFoundError: 图片文件不存在
        VisionError: 图像分析失败
    """
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_asr.py -v

# 运行特定测试函数
pytest tests/test_asr.py::test_transcribe -v

# 显示覆盖率
pytest tests/ --cov=src/video2markdown --cov-report=html
```

### 编写测试

- 所有新功能都应包含单元测试
- 测试文件命名：`test_<module>.py`
- 测试函数命名：`test_<function_name>`

```python
# tests/test_vision.py
def test_should_analyze_image_ppt():
    """测试 PPT 图片应被分析。"""
    result, reason = should_analyze_image("ppt_screenshot.jpg", None)
    assert result is True
    assert "PPT" in reason
```

## 提交规范

### 提交信息格式

```
<type>: <subject>

<body>

<footer>
```

### 类型说明

| 类型 | 说明 |
|-----|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能）|
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具链 |

### 示例

```
feat: 添加 PDF 输出格式支持

- 实现 PDFRenderer 类
- 添加 --format 命令行参数
- 更新文档

Closes #123
```

## 开发工作流

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 开发代码
# 编写测试
# 运行测试确保通过
pytest tests/

# 格式化代码
black src/ tests/
ruff check src/ tests/
```

### 3. 提交更改

```bash
git add .
git commit -m "feat: 添加某某功能"
```

### 4. 推送到远程

```bash
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

- 在 GitHub 上创建 PR
- 描述清楚 PR 的内容和目的
- 确保 CI 检查通过

## 项目结构

```
video_process/
├── src/video2markdown/    # 源代码
│   ├── __init__.py
│   ├── cli.py            # 命令行接口
│   ├── config.py         # 配置管理
│   ├── asr.py            # 语音识别
│   ├── audio.py          # 音频处理
│   ├── video.py          # 视频处理
│   ├── vision.py         # 图像分析
│   └── document.py       # 文档生成
├── tests/                 # 测试代码
├── docs/                  # 文档
│   ├── Requirements.md
│   └── ARCHITECTURE.md
├── testbench/             # 测试数据
│   ├── input/            # 输入视频
│   └── output/           # 输出文档
├── .agents/              # Agent 配置
├── README.md
├── CONTRIBUTING.md        # 本文件
├── pyproject.toml
└── setup.sh
```

## 添加新功能

### 添加新的命令行参数

编辑 `src/video2markdown/cli.py`：

```python
@click.option(
    "--new-param",
    type=click.INT,
    default=30,
    help="参数说明"
)
```

### 添加新的配置项

编辑 `src/video2markdown/config.py`：

```python
class Settings(BaseSettings):
    new_param: int = 30  # 默认值
```

编辑 `.env.example`：

```bash
# 新配置项说明
KIMI_NEW_PARAM=30
```

## 常见问题

### 1. Whisper 编译失败

```bash
# 确保安装了 cmake 和构建工具
sudo apt-get install cmake build-essential

# 在 whisper.cpp 目录下重新编译
cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
```

### 2. 测试失败

```bash
# 确保安装了开发依赖
pip install -e ".[dev]"

# 检查 .env 配置
# 某些测试需要有效的 API Key
```

### 3. 代码格式化检查失败

```bash
# 自动格式化
black src/ tests/

# 自动修复 ruff 问题
ruff check --fix src/ tests/
```

## 获取帮助

- 查看 [架构设计文档](docs/ARCHITECTURE.md) 了解系统设计
- 查看 [需求文档](docs/Requirements.md) 了解功能规划
- 提交 Issue 描述问题或建议
- 创建 Discussion 进行技术讨论

## 行为准则

- 尊重他人，友善交流
- 欢迎新手，耐心指导
- 专注于技术，避免无关争论
- 保护用户隐私，不泄露敏感信息

感谢您的贡献！🎉
