# Prompts 目录

此目录包含 Video2Markdown 项目中使用的所有 AI Prompt 模板。

## 文件格式

Prompt 文件使用 **YAML Frontmatter + Markdown** 格式：

```markdown
---
name: prompt-name
version: "1.0.0"
description: Prompt 用途描述
tags: [tag1, tag2]
models:
  - kimi-k2.5
parameters:
  temperature: 1
variables:
  - var1
  - var2
user_template: |
  可选的用户消息模板，支持 {var1} 变量替换
---

# Prompt 正文

使用 Markdown 格式编写 system prompt 内容...
```

### Frontmatter 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Prompt 标识名称 |
| `version` | string | 语义化版本号 |
| `description` | string | 用途说明 |
| `tags` | list | 分类标签 |
| `models` | list | 适用模型列表 |
| `parameters` | dict | API 参数（temperature, max_tokens 等） |
| `variables` | list | 模板变量列表 |
| `user_template` | string | 可选的用户消息模板 |

## 模型版本选择

同一 Prompt 可为不同模型编写优化版本，文件命名优先级：

1. `{name}.{model}.md` - 精确匹配（如 `image_analysis.kimi-k2.5.md`）
2. `{name}.{prefix}.md` - 前缀匹配（如 `image_analysis.kimi.md`）
3. `{name}.md` - 通用回退

## 文件说明

| 文件 | 用途 | 调用阶段 |
|-----|------|---------|
| `document_generation.md` | 文档生成主 Prompt | Stage 3: AI 文档生成 |
| `image_analysis.md` | 图片分析 Prompt | Stage 4: 智能配图 |
| `text_cleaning.md` | 文本清洗参考 Prompt | Stage 3 内部使用 |

## 使用方式

通过 PromptLoader 加载和使用：

```python
from video2markdown.prompts import get_loader

# 加载 Prompt（自动选择模型最优版本）
loader = get_loader()
prompt = loader.load("document_generation", model="kimi-k2.5")

# 渲染消息
messages = prompt.render_messages(
    title="My Video",
    duration=600,
    user_content=json.dumps(data)
)

# 调用 AI
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=messages,
    **prompt.get_api_params()
)
```

## 自定义调整

你可以编辑这些 Prompt 文件来微调 AI 的行为：

1. **调整输出风格**：修改语言风格、详细程度
2. **增加规则**：添加特定的处理规则
3. **修改格式**：调整输出格式要求
4. **版本升级**：修改后请升级 `version` 字段

**注意**：修改后请测试以确保 JSON 格式仍能正确解析。

## Prompt 设计原则

1. **角色明确**：每个 Prompt 都定义了 AI 的角色
2. **输入输出清晰**：明确说明输入格式和输出格式
3. **规则具体**：处理规则尽量具体、可执行
4. **语言统一**：所有输出要求使用简体中文
5. **版本管理**：使用 Frontmatter 记录版本和变更
