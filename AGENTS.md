# 项目开发指南

本项目使用 Vibe Coding（AI 协作开发）方法论。

## AI 助手上下文恢复

**首次进入项目时，AI 助手应检查 `.ai-context/*.md`**：
- 如有会话记录，询问用户是否恢复上下文
- 支持恢复单个或多个会话
- 恢复后可删除历史文件，避免堆积

**会话结束时**：
- 整理本次关键决策和进展
- 写入 `.ai-context/session-YYYY-MM-DD.md`
- 文件被 Git 完全忽略（不会提交到版本控制）

## 启用的 Skills

通过 `.skill-set` 声明，当前启用：
<!-- AI 读取 .skill-set 加载对应技能 -->

**技能加载协议**：
1. **Metadata 层**：读取每个 skill 的 name/description
2. **Core 层**：加载 SKILL.md 指导工作流
3. **按需层**：需要时加载 references/ 和 patterns/
4. **禁止**：不要一次性加载大代码库

## 项目信息

### 技术栈
- 语言：[填写主要语言，如 C/C++/Python]
- 平台：[填写目标平台，如 STM32/Linux/嵌入式 Linux]
- 构建工具：[如 Make/CMake/Meson]

### 目录结构
```
├── src/                # 源代码
├── include/            # 头文件
├── tests/              # 测试代码
├── docs/               # 文档
├── scripts/            # 项目脚本
├── skills/             # 链接的技能（自动创建）
└── .skill-set          # 技能声明
```

## 开发规范

### 代码规范
- 语言标准：[如 C11/C++17/Python 3.10]
- 缩进：[空格/Tab，数量]
- 文件长度：建议 <500 行
- 函数长度：建议 <50 行

### 命名规范
- 文件：小写，下划线分隔
- 函数：`模块名_动词_名词`，如 `gpio_init_pin`
- 变量：小写，下划线分隔
- 宏定义：全大写，下划线分隔

### 注释规范
- 文件头：功能说明、作者、日期
- 函数：参数、返回值、功能说明
- 复杂逻辑：解释"为什么"

## 工作流

### 1. 代码提交（参考 git-commits skill）

```bash
# 禁止操作
# [X] git add .
# [X] git commit -am "message"

# 正确操作
# [OK] 精确添加
git add src/file1.c src/file2.h

# [OK] 规范提交
git commit -m "feat(gpio): add interrupt debounce support"
```

**Commit Message 格式**：
```
<type>(<scope>): <subject>

<body>
```

- `type`: feat/fix/docs/style/refactor/test/chore
- `scope`: 模块名（可选）
- `subject`: 简短描述（<50 字符）

### 2. 质量门禁（参考 quality-gates skill）

提交前必须运行：

```bash
./scripts/gate.sh
```

或手动检查：
- [ ] 代码可编译
- [ ] 无编译警告（`-Wall -Werror`）
- [ ] 静态检查通过（如有）
- [ ] 测试通过（如有）

### 3. PR 流程（参考 pr-workflow skill）

```bash
# 1. 创建功能分支
git checkout -b feature/xxx

# 2. 开发并提交
# ...

# 3. 本地检查
./scripts/gate.sh

# 4. 推送
git push -u origin feature/xxx

# 5. 创建 PR（使用模板）

# 6. 审查后合并
```

## 多代理安全规则（强制）

### 绝对禁止操作

- [X] 创建 `git stash`
- [X] 切换分支（除非明确要求）
- [X] 修改 `.worktrees/`
- [X] 使用 `git add -A` 或 `git commit -a`
- [X] 直接 push 到 main/master
- [X] 未经明确指令执行 `git push`

### 推送确认流程（强制执行）

**AI 助手执行 `git push` 前必须遵守以下流程**：

```
1. 检查用户是否在本次对话中明确说"推送"或"push"
   ↓
2. 如果没有，必须询问用户："是否推送到远程仓库？"
   ↓
3. 等待用户明确回答 [是/确认/推送] 或 [否/取消/不推送]
   ↓
4. 仅当用户明确确认后才可执行
```

**关键原则**：
- [X] **禁止假设**：即使前面对话中用户说过推送，**每次**都要重新确认
- [X] **禁止推测**：不能根据"上下文暗示"判断用户想推送
- [X] **明确指令**：必须看到"推送"、"push"、"提交到远程"等明确词汇

### 允许操作

- [OK] 在当前分支精确提交
- [OK] 查看状态/日志/diff
- [OK] 创建功能分支
- [OK] 用户明确要求后执行推送

### 禁止擅自扩展

- [X] **不要**擅自创建用户未要求的文件、脚本、配置
- [X] **不要**添加超出用户明确指令范围的功能或机制
- [X] **不要**以"优化"、"完善"等理由添加额外内容
- [OK] 只执行用户明确要求的修改
- [OK] 如有建议，先询问用户确认

## 工具脚本

项目提供以下脚本（根据实际项目调整）：

- `scripts/gate.sh` - 质量门禁检查
- `scripts/commit.sh` - 精确提交辅助
- `scripts/build.sh` - 项目构建
- `scripts/test.sh` - 运行测试
- `scripts/link-skills.sh` - 链接技能库

## 调试指南

### 常见问题

#### 问题 1：[描述常见问题]
**现象**：
**原因**：
**解决**：

#### 问题 2：编译失败
**现象**：链接错误，找不到符号
**原因**：可能是头文件路径或库链接顺序问题
**解决**：
1. 检查 include 路径
2. 检查 Makefile 中的库顺序

## Skill 迭代

开发中发现 skill 问题或改进点：

1. **快速记录**：添加到 `.skill-updates-todo.md`
   ```markdown
   - [ ] stm32-gpio: 补充 H7 系列 PWR 配置
   ```

2. **直接修改**：编辑 `~/skills-registry/` 中的对应 skill
   ```bash
   cd ~/skills-registry
   vim skills/embedded/mcu/st-stm32/SKILL.md
   ```

3. **提交变更**：
   ```bash
   cd ~/skills-registry
   git add .
   git commit -m "fix(stm32): 补充 H7 PWR 配置说明"
   git push
   ```

## 项目特定知识

### [模块 1 名称]
[该模块的特殊要求或注意事项]

### [模块 2 名称]
[该模块的特殊要求或注意事项]

## 参考资料

- [项目文档链接]
- [外部参考链接]

---

*本文件供 AI 助手阅读，指导开发流程*
*基于 Skills Registry 中的 dev-workflow 技能集*

**修改历史**：
- 2026-02-11: 初始创建
