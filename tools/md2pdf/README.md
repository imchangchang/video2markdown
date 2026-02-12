# Markdown to PDF Converter

将 Markdown 文件转换为 PDF 的独立小工具。

## 特点

- 📝 **纯 Python 实现** - 无需外部命令行工具（如 pandoc/wkhtmltopdf）
- 🎨 **内置样式** - 提供默认和 GitHub 两种样式
- 🖼️ **图片支持** - 自动处理 Markdown 中的本地图片
- 🔤 **中文优化** - 针对中文内容优化字体和排版
- 📄 **高质量输出** - 使用 WeasyPrint 生成出版级 PDF

## 安装

### 1. 安装 Python 依赖

```bash
cd tools/md2pdf
pip install -r requirements.txt
```

### 2. 安装系统依赖（WeasyPrint 需要）

**Ubuntu/Debian:**
```bash
sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

**macOS:**
```bash
brew install pango
```

**Windows:**
- 安装 [GTK+ for Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
- 或安装 [WeasyPrint for Windows](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

## 使用

### 基础用法

```bash
# 转换 Markdown 为 PDF（输出同名 .pdf 文件）
python md2pdf.py document.md

# 指定输出文件名
python md2pdf.py document.md -o output.pdf
```

### 样式选择

```bash
# 使用默认样式（适合阅读）
python md2pdf.py document.md

# 使用 GitHub 样式（类似 GitHub 渲染效果）
python md2pdf.py document.md --style github
```

### 自定义样式

```bash
# 添加自定义 CSS
python md2pdf.py document.md --css custom.css
```

### 完整示例

```bash
# 转换 Video2Markdown 生成的文档
python md2pdf.py ../../test_outputs/results/full_usb/USB的调试过程以及调试方法.md \
    --style github \
    -o USB调试指南.pdf
```

## 支持的 Markdown 特性

- ✅ 标题（H1-H6）
- ✅ 段落和换行
- ✅ 粗体、斜体、删除线
- ✅ 代码块和行内代码
- ✅ 引用块
- ✅ 有序/无序列表
- ✅ 表格
- ✅ 链接和图片
- ✅ 水平分割线
- ✅ 中文内容优化

## 文件结构

```
tools/md2pdf/
├── md2pdf.py          # 主脚本
├── requirements.txt   # 依赖
└── README.md         # 本文档
```

## 注意事项

1. **图片路径** - 工具会自动解析 Markdown 中的相对路径图片，请确保图片文件存在
2. **中文字体** - 系统需要安装中文字体（如 Noto Sans CJK、Microsoft YaHei 等）
3. **文件大小** - 大量高清图片可能导致 PDF 文件较大

## 故障排除

### ImportError: 找不到 Pango

```bash
# Ubuntu/Debian
sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# macOS
brew install pango
```

### 中文显示为方块

系统缺少中文字体，安装字体：

```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# macOS (通常已自带)
brew install font-noto-sans-cjk
```

### 图片不显示

确保 Markdown 中的图片路径是相对路径，且图片文件存在于相对于 Markdown 文件的位置。

## 许可证

与主项目相同：MIT License
