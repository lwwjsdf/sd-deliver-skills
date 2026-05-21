---
name: tracking-setup-e2e
description: 客户新项目启动或新业务场景需要完整数据采集和分析能力时使用
---

# 埋点全链路交付

## 适用场景

- 客户新项目启动，需要从零建立数据采集体系
- 现有业务新增功能，需要补充埋点和分析看板
- 需要将测试环境配置迁移到客户生产环境

## 核心原则（Iron Law）

**必须先完成采集方案设计并经客户确认，再进行后续任何步骤。**

不允许在方案未确认的情况下造数或创建看板。违反此原则会导致返工。

## 前置条件

### 项目启动时（一次性配置）

在项目根目录复制 `.env.example` 为 `.env`，填入以下变量：

| 变量 | 必填时机 | 说明 | 获取方式 |
|------|----------|------|----------|
| `SA_HOST` | 项目启动 | 神策 CDP 地址 | 客户环境 URL，如 `https://demo.sensorsdata.cn` |
| `SA_PROJECT` | 项目启动 | 项目 ID | 登录后 URL 中 `project=` 的值 |
| `CLIENT_NAME` | 项目启动 | 客户名称 | 用于输出文件命名 |
| `TRACKING_PLAN_PATH` | Phase 2 完成后 | 埋点方案 Excel 路径 | 客户确认后的方案文件路径 |
| `SA_TOKEN` | Phase 4b（模拟数据导入）| 神策 HTTP API 数据接入 token | 神策后台 → 数据接入 → HTTP API → 复制 token |

> `SA_TOKEN` 是数据上报凭证（非登录认证），格式为 `https://<host>/sa?token=<token>`，只在模拟数据导入时需要，元数据导入（Phase 4a）不需要。

```bash
cp .env.example .env
# 编辑 .env，至少填入 SA_HOST、SA_PROJECT、CLIENT_NAME
```

### 浏览器登录态

Phase 4a 脚本通过 gstack/browse 自动导入 Chrome 登录 cookie，**无需手动操作**。

前提：
1. Chrome 中已登录目标神策环境
2. 已安装 gstack/browse（一次性）：
   ```bash
   npx skills add gstack/browse -g
   ```

## 执行阶段

### Phase 1：业务目标确认 👤

收集以下信息后才能进入 Phase 2：
- 核心业务场景（用户注册/购买/使用路径等）
- 需要回答的关键业务问题（转化率？留存？活跃度？）
- 分析维度（渠道、用户分群、时间粒度）
- 数据消费方（运营/产品/数据分析师）

输出：业务目标确认单（一页，列出以上四项）

### Phase 2：采集方案设计 👤

基于 Phase 1 输出，设计埋点方案：
- 事件列表（事件名、中文名、触发时机）
- 每个事件的属性列表（属性名、类型、示例值、是否必填）
- 用户属性列表（属性名、类型）

**等待客户确认后才能进入 Phase 3。确认后在 `.env` 中设置 `TRACKING_PLAN_PATH`。**

输出：埋点方案表（Excel，包含 Events / Details（Event） / Users 三个 sheet）

### Phase 3：模拟数据生成 🤖

在运行脚本前，先询问用户：
- 每个事件生成多少条记录？（建议 50，压测场景可用 500）
- 模拟多少个用户？（建议 20）

```bash
python3 tracking-setup-e2e/scripts/generate_mock_data.py --count <N> --users <M>
```

脚本自动读取 `.env` 中的 `TRACKING_PLAN_PATH` 和 `SA_PROJECT`，生成：
- `tracking-setup-e2e/mock_data/mock_events.jsonl` — 每行一条记录
- `tracking-setup-e2e/mock_data/mock_events_batch.txt` — base64 编码，可直接 POST

### Phase 4a：元数据导入 CDP 🤖

```bash
python3 tracking-setup-e2e/scripts/import_to_cdp.py
```

脚本自动完成：
1. 从 Chrome 导入登录态（无需手动操作）
2. 从 Excel `Events` sheet 读取事件列表，逐个创建元事件
3. 从 Excel `Details（Event）` sheet 读取每个事件的属性，写入对应事件
4. 从 Excel `Users` sheet 读取用户属性，批量写入

注意：系统保留字段名（如 `Id`、`PersonEmail`）会自动跳过并在输出中列出。

### Phase 4b：模拟数据导入 🤖

```bash
curl -X POST "${SA_HOST}/sa?token=${SA_TOKEN}" \
     -d 'data='$(cat tracking-setup-e2e/mock_data/mock_events_batch.txt)
```

### Phase 4c：看板创建 👤

按业务目标创建看板，参考 cdp-operations skill。截图存档。

### Phase 5：资产迁移 🤖

使用神策资产项工具将配置元数据从测试环境迁移到客户生产环境：
1. 导出测试环境资产（看板、标签、事件定义）
2. 检查资产依赖关系
3. 导入客户生产环境
4. 验证迁移结果

输出：资产迁移记录（迁移项清单 + 验证截图）

## 输出模板

```
## 交付物清单

- [ ] 业务目标确认单
- [ ] 埋点方案表（已客户确认）
- [ ] 模拟数据文件
- [ ] 元数据导入确认（import_to_cdp.py 输出日志）
- [ ] 看板截图
- [ ] 资产迁移记录
```

## 常见问题

**客户说"先做再确认"：** 坚持 Phase 2 确认门。方案变更后造数和看板全部作废，返工成本远高于等待确认的时间。

**import_to_cdp.py 报"缺少必要配置"：** 检查项目根目录是否有 `.env` 文件，以及对应变量是否已填写。

**import_to_cdp.py 报"登录态导入失败"：** 确认 Chrome 中已登录目标神策环境（`SA_HOST` 对应的域名）。

**字段创建报 ALREADY_EXISTS：** 正常，脚本自动跳过，不影响其他字段。

**元事件属性写入失败（10005 错误）：** 通常是事件上有特殊关联字段，脚本已自动处理常见情况。如仍报错，检查事件是否有虚拟字段依赖。

**模拟数据不够真实：** 向客户要 1-2 个真实业务场景的描述，按真实路径生成数据。
