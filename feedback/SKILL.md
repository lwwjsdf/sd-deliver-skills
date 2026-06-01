---
name: sd-feedback
version: 0.1.0
description: |
  记录 sdeliver skill 使用过程中发现的问题或改进建议。
  在任何 skill 使用过程中，随时说 "/sd-feedback <内容>" 即可记录。
  例：/sd-feedback sd-tracking-setup-e2e 的脚本路径应该用绝对路径
allowed-tools:
  - Bash
---

# sd-feedback

将用户描述的问题或建议写入 `~/.sdeliver/feedback/`，供后续在 Claude Code 中处理。

## 执行步骤

### Step 1：解析输入

从用户的输入中提取：
- **关联 skill**：用户提到了哪个 skill（如 `sd-tracking-setup-e2e`）；未提及则填 `sdeliver`
- **类型**：根据描述判断
  - `prompt-fix` — SKILL.md 指令有歧义、描述不准确、AI 走了弯路
  - `script-bug` — 脚本执行报错、参数错误、路径问题
  - `missing-feature` — 缺少某个功能
  - `ux-improvement` — 交互体验问题、流程不顺畅
- **严重程度**：
  - `high` — 导致工作流中断或数据错误
  - `medium` — 需要绕路但能继续
  - `low` — 体验问题，不影响结果
- **内容**：用户描述的原文

### Step 2：生成文件名

格式：`<YYYY-MM-DD>-<skill-name>-<slug>.md`

slug 从描述中提取 2-4 个关键词，用连字符连接，全小写英文。
例：`2026-06-01-sd-tracking-setup-e2e-script-path-absolute.md`

获取当前日期：
```bash
date +%Y-%m-%d
```

### Step 3：写入文件

```bash
mkdir -p ~/.sdeliver/feedback
```

写入以下格式：

```markdown
---
skill: <skill-name>
type: <type>
severity: <severity>
date: <YYYY-MM-DD>
---

## 发生了什么
<用户描述的原文，保持原意，可适当整理>

## 期望行为
<根据描述推断应该怎样才对，不确定则留空>

## 建议修改
<具体改哪里，不确定则留空>
```

### Step 4：确认

写完后告知用户：
```
✅ 已记录到 ~/.sdeliver/feedback/<文件名>
   回到 Claude Code 后调用 /sdeliver 可查看待处理反馈。
```
