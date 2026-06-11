---
name: sd-feedback
version: 0.2.0
description: |
  记录 sdeliver skill 使用过程中发现的问题或改进建议。
  在任何 skill 使用过程中，随时说 "/sd-feedback <内容>" 即可记录。
  例：/sd-feedback sd-tracking-setup-e2e 的脚本路径应该用绝对路径
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# sd-feedback

将用户描述的问题或建议写入 `~/.sdeliver/feedback/`，供后续在 Claude Code 中处理。

**反馈闭环：** 本 skill 负责记录，FAQ 负责消费。反馈经分类评审后，符合 FAQ 收录标准的将反向回填到 `sd-faq` 对应 Topic，形成「问题发现 → 记录 → 评审 → 知识沉淀」闭环。

## 执行步骤

### Step 1：解析输入

从用户的输入中提取：
- **关联 skill**：用户提到了哪个 skill（如 `sd-tracking-setup-e2e`）；未提及则填 `sdeliver`
- **类型**：根据描述判断（见下方「反馈类型与处理路径」）
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
status: open
---

## 发生了什么
<用户描述的原文，保持原意，可适当整理>

## 期望行为
<根据描述推断应该怎样才对，不确定则留空>

## 建议修改
<具体改哪里，不确定则留空>

## 处理记录
- <YYYY-MM-DD> 记录创建
```

### Step 4：确认

写完后告知用户：
```
✅ 已记录到 ~/.sdeliver/feedback/<文件名>
   类型：<type> | 严重度：<severity>
   处理路径：<见下方反馈类型与处理路径>
   回到 Claude Code 后调用 /sdeliver 可查看待处理反馈。
```

---

## 反馈类型与处理路径

| 类型 | 说明 | 处理路径 | 是否回填 FAQ |
|------|------|----------|:------------:|
| `prompt-fix` | SKILL.md 指令有歧义、描述不准确、AI 走了弯路 | 直接修改对应 skill 的 SKILL.md | ✅ 是（更新 FAQ 关联 skill 引用） |
| `script-bug` | 脚本执行报错、参数错误、路径问题 | 修复脚本 → 更新 skill 版本号 | ❌ 否（技术问题，不入 FAQ） |
| `missing-feature` | 缺少某个功能 | 评估后纳入迭代计划 | ❌ 否（功能需求，不入 FAQ） |
| `ux-improvement` | 交互体验问题、流程不顺畅 | 优化流程 → 更新 SKILL.md 步骤 | ✅ 是（如为高频痛点） |
| `faq-candidate` | 客户高频问题，当前 FAQ 未覆盖 | 直接回填到 `sd-faq` 对应 Topic | ✅ 是（核心闭环） |
| `doc-inconsistency` | 多 skill 文档间描述矛盾 | 统一修正 → 同步更新 FAQ | ✅ 是 |

### 定稿流程（faq-candidate 类型）

一条反馈要进入 FAQ，需经过以下评审：

1. **出现频率**：同一问题被记录 ≥2 次，或一次但影响严重（high）
2. **可复现性**：有明确的触发条件和解决步骤
3. **通用性**：不局限于特定客户或特定版本
4. **导航层适配**：FAQ 只收快速决策/陷阱/排查步骤，不收详细执行流程

满足以上条件后，按以下格式回填到 `sd-faq`：

```markdown
### 常见问题（来自 `/sd-feedback` 沉淀）

**<问题简述>：**
<一句话答案或决策规则>
> 来源：feedback/<YYYY-MM-DD>-<skill>-<slug>.md
```

### 关联 skill 更新同步

当反馈导致 skill 内容变更时，FAQ 需同步检查：

| skill 变更类型 | FAQ 同步动作 |
|---------------|-------------|
| Phase/Step 编号调整 | 更新 FAQ 中所有关联引用 |
| 新增常见问题节 | 反向回填到 FAQ 对应 Topic |
| 删除或合并 Phase | 删除 FAQ 中失效引用，更新为新的入口 |
| 版本号升级（0.x → 0.y） | 检查 FAQ 中版本相关描述是否需要更新 |

**同步检查清单（每次 skill 发布时执行）：**
- [ ] FAQ 中引用的 Phase/Step 编号与 skill 当前版本一致
- [ ] FAQ 中「已知陷阱」列表包含该 skill 最新 Iron Law
- [ ] FAQ 中「常见问题」子节覆盖该 skill 高频问题
- [ ] 如有新增 Topic，更新 FAQ 顶部「使用方式」示例列表

---

## 批量处理反馈（维护者模式）

当需要批量处理积累的反馈时：

```bash
# 列出所有待处理反馈
ls -la ~/.sdeliver/feedback/*.md

# 按类型统计
for t in prompt-fix script-bug missing-feature ux-improvement faq-candidate doc-inconsistency; do
  echo "$t: $(grep -l "type: $t" ~/.sdeliver/feedback/*.md 2>/dev/null | wc -l)"
done

# 按 skill 统计
for skill in $(grep "^skill:" ~/.sdeliver/feedback/*.md 2>/dev/null | sed 's/.*: //' | sort | uniq); do
  echo "$skill: $(grep -l "skill: $skill" ~/.sdeliver/feedback/*.md 2>/dev/null | wc -l)"
done
```

处理完成后，更新反馈文件中的 `status` 字段：
- `open` → 待处理
- `resolved` → 已修复/已回填
- `wontfix` → 不处理（需注明原因）
- `duplicate` → 重复反馈（关联到主反馈文件）
