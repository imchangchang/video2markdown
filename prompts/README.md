# Prompts 目录

此目录包含 Video2Markdown 项目中使用的所有 AI Prompt 模板。

## 文件说明

| 文件 | 用途 | 调用阶段 |
|-----|------|---------|
| `document_generation.md` | 文档生成主 Prompt | Stage 3: AI 文档生成 |
| `image_analysis.md` | 图片分析 Prompt | Stage 4: 智能配图 |
| `text_cleaning.md` | 文本清洗参考 Prompt | Stage 3 内部使用 |

## 使用方式

Prompt 文件在运行时被读取并传递给 AI API：

```python
# 读取 Prompt
with open("prompts/document_generation.md", "r") as f:
    system_prompt = f.read()

# 调用 AI
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
)
```

## 自定义调整

你可以编辑这些 Prompt 文件来微调 AI 的行为：

1. **调整输出风格**：修改语言风格、详细程度
2. **增加规则**：添加特定的处理规则
3. **修改格式**：调整输出格式要求

**注意**：修改后请测试以确保 JSON 格式仍能正确解析。

## Prompt 设计原则

1. **角色明确**：每个 Prompt 都定义了 AI 的角色
2. **输入输出清晰**：明确说明输入格式和输出格式
3. **规则具体**：处理规则尽量具体、可执行
4. **语言统一**：所有输出要求使用简体中文
