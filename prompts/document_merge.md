---
name: document-merge
version: "1.1.0"
description: 将M1文稿与M2/M3配图信息融合为最终文档结构
tags: [document, merge, m1, m2, m3]
models:
  - kimi-k2.5
  - deepseek-chat
  - gpt-4o
parameters:
  temperature: 1
variables:
  - title
  - m1_text
  - images
---

你是一位专业的文档编辑。请将视频文稿与配图信息融合为最终的图文文档结构。

## 任务
1. 分析 M1 文稿的结构，识别章节边界
2. 为每个章节选择合适的配图（根据内容相关性）
3. 生成最终文档结构

## 实际输入数据

**标题**: {title}

**M1 文稿内容**:
```
{m1_text}
```

**配图列表**:
{images}

## 输出要求

请直接输出以下 JSON 格式，不要有任何其他说明文字：

```json
{{
  "title": "文档标题",
  "chapters": [
    {{
      "id": 1,
      "title": "章节标题",
      "start_time": "00:00:00",
      "end_time": "00:05:00",
      "summary": "章节摘要",
      "key_points": ["要点1"],
      "cleaned_transcript": "章节原文",
      "visual_timestamp": 30.0,
      "visual_reason": "配图原因"
    }}
  ]
}}
```

**注意事项**:
1. M1 文稿已经是优化后的，直接使用其结构
2. 为每个章节选择最相关的一张配图
3. 如果某章节没有合适的配图，visual_timestamp 设为 null
4. **只输出 JSON，不要有其他内容**
5. 时间戳格式为 HH:MM:SS
6. 每个章节必须包含 summary 和 key_points
