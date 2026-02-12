# 测试指南

## 目录结构

```
tests/
├── conftest.py           # pytest fixtures 配置
├── fixtures/             # 小型静态测试数据（入 git）
│   ├── sample_segments.json
│   └── sample_video_info.json
├── integration/          # 集成测试
├── unit/                 # 单元测试
└── README.md             # 本文件
```

## 测试数据管理

### 1. 小型静态数据（tests/fixtures/）

用于单元测试的小型数据文件（<1MB），随代码版本控制：

- `sample_segments.json` - 转录片段示例
- `sample_video_info.json` - 视频元数据示例

添加新的 fixture：
```bash
# 直接放入 fixtures 目录
cp my_data.json tests/fixtures/
```

在测试中使用：
```python
def test_with_fixture():
    from conftest import load_json_fixture
    data = load_json_fixture("my_data.json")
```

### 2. 大型测试视频（testdata/videos/）

**不纳入 git 管理**，需手动放置：

```bash
# 放置测试视频
cp my_video.mp4 testdata/videos/
```

在测试中使用：
```python
def test_with_video(get_test_video):
    video_path = get_test_video
    # 处理视频...
```

如果目录为空，测试会自动跳过并提示：
```
SKIPPED [1] tests/conftest.py:85: No test videos found in: testdata/videos
```

### 3. 临时文件处理

**推荐：使用 pytest 的 `tmp_path`**

```python
def test_something(tmp_path):
    # tmp_path 是每个测试的唯一临时目录
    output_file = tmp_path / "output.md"
    
    # 测试代码...
    process_video(input_video, output_file)
    
    # 断言
    assert output_file.exists()
    
    # 测试结束后自动清理
```

**调试时保留输出：使用 `debug_output_dir`**

```python
def test_with_debug(debug_output_dir):
    # 文件会保留在 test_outputs/results/<test_name>/
    output_file = debug_output_dir / "debug_result.md"
    
    process_video(input_video, output_file)
    
    # 测试后可手动查看 test_outputs/results/test_with_debug/
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试（需要测试视频）
pytest tests/integration/ -v

# 只运行有测试视频的测试
pytest tests/ -v --ignore-glob="*no_video*"

# 保留失败测试的输出
pytest tests/ -v --tb=short
```

## 测试输出目录

```
test_outputs/
├── temp/                 # 临时文件（每次测试前清空）
└── results/              # 调试输出（按测试名组织）
    └── test_something/   # 具体测试的输出
```

**清理输出**：
```bash
# 清理所有输出
rm -rf test_outputs/*

# 或保留 .gitkeep
find test_outputs -type f ! -name '.gitkeep' -delete
```

## 添加新测试

### 单元测试（tests/unit/）

不依赖外部资源，运行快速：

```python
# tests/unit/test_my_module.py
def test_function_logic():
    result = my_function(["item1", "item2"])
    assert len(result) == 2
```

### 集成测试（tests/integration/）

需要测试视频或其他外部资源：

```python
# tests/integration/test_video_pipeline.py
def test_full_pipeline(get_test_video, tmp_path):
    video_path = get_test_video
    output_path = tmp_path / "output.md"
    
    # 运行完整流程
    result = process_video(video_path, output_path)
    
    assert output_path.exists()
    assert len(result.chapters) > 0
```

## 最佳实践

1. **优先使用动态生成数据** - 75% 的测试数据应代码生成
2. **大型文件不放 git** - 使用 testdata/videos/ 手动管理
3. **使用 tmp_path** - 自动清理临时文件
4. **调试输出用 debug_output_dir** - 方便查看中间结果
5. **跳过而非失败** - 缺少测试视频时跳过而非失败
