# Whisper.cpp 配置指南

本文档说明如何在不同平台上配置 whisper.cpp，以及如何替换项目内置的版本。

## 项目内置版本

本项目在 `tools/whisper-cpp/` 目录下预置了编译好的 whisper-cli，包含：

| 组件 | 说明 |
|------|------|
| `whisper-cli` | 主程序（动态链接） |
| `whisper-cli-wrapper` | 包装脚本（自动设置库路径） |
| `lib/` | 依赖的共享库 |

### 当前内置版本信息

- **平台**: x86_64 Linux (GNU/Linux 3.2.0+)
- **编译选项**: CMake 默认配置
- **依赖**: libstdc++, libgomp (OpenMP)

### 使用方法

项目会自动检测并使用内置版本，无需额外配置：

```bash
# 内置版本已通过 wrapper 脚本自动配置库路径
uv run python -m video2markdown transcribe audio.wav
```

如需手动测试内置版本：

```bash
# 使用 wrapper 脚本（推荐）
./tools/whisper-cpp/whisper-cli-wrapper --help

# 或直接调用（需设置 LD_LIBRARY_PATH）
LD_LIBRARY_PATH=./tools/whisper-cpp/lib ./tools/whisper-cpp/whisper-cli --help
```

---

## 为其他平台编译 whisper.cpp

如果你使用的平台与内置版本不兼容（如 ARM、macOS、Windows），需要自行编译。

### 1. 获取源码

```bash
# 克隆 whisper.cpp 仓库
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# 检出稳定版本（推荐）
git checkout v1.7.5  # 或其他稳定标签
```

### 2. 安装依赖

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install cmake build-essential
```

#### macOS
```bash
# 安装 Xcode Command Line Tools
xcode-select --install

# 或使用 Homebrew
brew install cmake
```

#### Windows
```powershell
# 使用 vcpkg 或手动安装 CMake + Visual Studio
```

### 3. 编译

#### Linux/macOS (CMake)

```bash
# 基本编译
cmake -B build
cmake --build build --config Release

# 启用特定优化（如 AVX/NEON）
cmake -B build -DWHISPER_AVX=ON -DWHISPER_AVX2=ON -DWHISPER_FMA=ON
cmake --build build --config Release

# ARM 平台 (Raspberry Pi 等)
cmake -B build -DWHISPER_NO_AVX=ON
cmake --build build --config Release
```

编译完成后，二进制文件位于：
- `build/bin/whisper-cli` (Linux/macOS)
- `build/bin/Release/whisper-cli.exe` (Windows)

#### 静态链接（推荐用于分发）

```bash
# Linux 静态链接
cmake -B build -DBUILD_SHARED_LIBS=OFF
cmake --build build --config Release
```

### 4. 替换项目内置版本

编译完成后，将新的二进制文件复制到项目目录：

```bash
# 备份原有版本
mv tools/whisper-cpp tools/whisper-cpp.bak

# 创建新目录结构
mkdir -p tools/whisper-cpp/lib

# 复制新的 whisper-cli
# 情况 A: 动态链接版本
cp /path/to/your/whisper.cpp/build/bin/whisper-cli tools/whisper-cpp/
cp /path/to/your/whisper.cpp/build/src/libwhisper*.so* tools/whisper-cpp/lib/ 2>/dev/null || true
cp /path/to/your/whisper.cpp/build/ggml/src/libggml*.so* tools/whisper-cpp/lib/ 2>/dev/null || true

# 情况 B: 静态链接版本（无需复制库文件）
# cp /path/to/your/whisper.cpp/build/bin/whisper-cli tools/whisper-cpp/

# 复制 wrapper 脚本
cp tools/whisper-cpp.bak/whisper-cli-wrapper tools/whisper-cpp/

# 设置执行权限
chmod +x tools/whisper-cpp/whisper-cli tools/whisper-cpp/whisper-cli-wrapper
```

### 5. 验证

```bash
# 测试内置版本
./tools/whisper-cpp/whisper-cli-wrapper --help

# 运行项目测试
uv run pytest tests/ -v -k whisper
```

---

## 常见问题

### Q: 内置版本报错 "cannot open shared object file"

**A**: 使用 wrapper 脚本，它会自动设置 `LD_LIBRARY_PATH`：
```bash
./tools/whisper-cpp/whisper-cli-wrapper --help
```

### Q: ARM 平台（如树莓派）如何编译？

**A**: 
```bash
cmake -B build -DWHISPER_NO_AVX=ON -DWHISPER_NO_AVX2=ON -DWHISPER_NO_FMA=ON
cmake --build build
```

### Q: macOS 上如何编译 ARM (Apple Silicon) 版本？

**A**:
```bash
cmake -B build -DWHISPER_METAL=ON  # 启用 Metal GPU 加速
cmake --build build --config Release
```

### Q: 我不想替换内置版本，如何使用自定义版本？

**A**: 项目按以下优先级查找 whisper-cli：
1. `tools/whisper-cpp/whisper-cli-wrapper`（内置版本）
2. `tools/whisper-cpp/whisper-cli`（内置版本）
3. `whisper.cpp/build/bin/whisper-cli`（向后兼容）
4. 系统 PATH 中的 `whisper-cli`

你可以：
- 将自定义版本放在系统 PATH 中
- 或设置环境变量指向自定义版本：
  ```bash
  # 在 .env 文件中添加
  KIMI_WHISPER_CLI=/path/to/your/whisper-cli
  ```
  然后修改 `config.py` 读取此环境变量

### Q: 如何查看当前使用的 whisper-cli 路径？

**A**:
```bash
uv run python -c "from video2markdown.config import settings; print(settings.resolve_whisper_cli())"
```

---

## 参考链接

- [whisper.cpp GitHub](https://github.com/ggerganov/whisper.cpp)
- [whisper.cpp 编译文档](https://github.com/ggerganov/whisper.cpp/blob/master/README.md#build)
