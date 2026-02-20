# 04-API超时问题修复

## 问题确认

**错误类型**: `openai.APITimeoutError` / `httpx.ReadTimeout`  
**发生位置**: Stage 6 (`stage6_generate.py:73`)  
**影响视频**: 
- Skills (20m3s) - 失败
- 闪客 (14m45s) - 失败

## 根因分析

| 视频 | Stage 6 实际耗时 | 原超时 | 结果 |
|-----|----------------|--------|------|
| Skills | 390.4s | 120s | ❌ 超时 |
| 闪客 | 385.4s | 120s | ❌ 超时 |

**原因**: Stage 6 请求体大（40k-60k字符），AI 处理需 3-6 分钟

## 修复方案

### 修改 1: config.py
```python
def get_client_kwargs(self, timeout: float = 600.0) -> dict:
    return {
        "api_key": self.api_key,
        "base_url": self.base_url,
        "timeout": timeout,  # 默认 600s
        "max_retries": 2,
    }
```

### 修改 2: stage6_generate.py
```python
# Stage 6 使用 900s 超长超时
timeout_seconds = 900.0
client = OpenAI(**settings.get_client_kwargs(timeout=timeout_seconds))
```

### 修改 3: 增加详细日志
- 请求体大小
- Token 预估
- 开始/结束时间戳

## 验证结果

| 视频 | 请求体 | 实际耗时 | 结果 |
|-----|--------|---------|------|
| Skills | 63,081字符 | 217.1s | ✅ 成功 |
| 闪客 | 39,828字符 | 147.8s | ✅ 成功 |

## 提交记录

```
a6049c5 fix(api-timeout): 修复长视频 Stage 6 API 超时问题
```
