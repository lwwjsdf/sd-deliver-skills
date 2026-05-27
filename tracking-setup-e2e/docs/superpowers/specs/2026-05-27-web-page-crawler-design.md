# Web 页面爬虫设计

**日期**: 2026-05-27
**状态**: 已批准
**范围**: tracking-setup-e2e 规则驱动造数模式 — Web 端属性精确化

---

## 背景

SA 全埋点 Web 标准属性（`$url`、`$title`、`$referrer`、`$url_path`）在未配置时 fallback 到随机值，不符合业务预期。

现有 `property_enums` 机制已支持简单列表枚举，`PropertyEnumResolver` 可直接处理 `$url`、`$title` 等标准属性。缺少的只是一个辅助工具，帮用户从真实网站自动生成这些枚举列表。

---

## 设计

### 定位

`crawl_web_pages.py` 是一个**可选的一次性辅助脚本**，不是造数流程的必要组件。用户在需要更精确的 Web 属性枚举时运行一次，将结果写入 `business_logic.yaml` 的 `property_enums` 区块。造数流程本身不变。

### 数据流

```
crawl_web_pages.py --url https://www.westk.hk/tc/home --output rules/special/westk/business_logic.yaml
  └─ BFS 爬取同域内部链接（默认深度 2）
       └─ 提取每页 URL + <title>
            └─ 生成 property_enums 的 $url / $title / $url_path 列表
                 └─ 写入（或打印）YAML 片段
                      └─ PropertyEnumResolver 直接读取，无需其他改动
```

### 脚本接口

```bash
# 打印 YAML 片段到 stdout（默认）
python3 scripts/crawl_web_pages.py --url https://www.westk.hk/tc/home

# 直接写入 YAML 文件的 property_enums 区块
python3 scripts/crawl_web_pages.py \
  --url https://www.westk.hk/tc/home \
  --output rules/special/westk/business_logic.yaml \
  --depth 2 \
  --max-pages 50
```

参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--url` | 必填 | 起始页面 URL |
| `--depth` | `2` | BFS 最大深度 |
| `--max-pages` | `50` | 最多爬取页面数 |
| `--output` | 无（打印到 stdout） | 写入目标 YAML 文件路径 |
| `--delay` | `0.5` | 请求间隔秒数（礼貌爬取） |

### 输出格式

脚本输出（或写入）的 YAML 片段，直接兼容 `property_enums` 区块：

```yaml
# 由 crawl_web_pages.py 生成，来源：https://www.westk.hk/tc/home
# 生成时间：2026-05-27
$url:
  - "https://www.westk.hk/tc/home"
  - "https://www.westk.hk/tc/arts-culture"
  - "https://www.westk.hk/tc/whats-on"
$title:
  - "首頁 | 西九文化區"
  - "藝術及文化 | 西九文化區"
  - "節目及活動 | 西九文化區"
$url_path:
  - "/tc/home"
  - "/tc/arts-culture"
  - "/tc/whats-on"
```

`$referrer` 不单独生成，造数时从 `$url` 列表中随机取另一个值即可（由 `PropertyEnumResolver` 的调用方处理，或直接复用 `$url` 枚举）。

### 写入行为（`--output` 模式）

- 若 `property_enums` 区块已存在：**合并**，只更新 `$url`、`$title`、`$url_path` 三个键，不覆盖其他键（如 `seatArea`、`ticketType` 等）
- 若 `property_enums` 区块不存在：在文件末尾追加
- 写入前打印将要修改的键列表，供用户确认

### 爬取逻辑

1. 从起始 URL 开始，BFS 遍历同域（`netloc` 相同）内部链接
2. 跳过：锚点链接（`#`）、文件下载（`.pdf`、`.zip` 等）、外部域名、已访问 URL
3. 每个页面提取：完整 URL、`<title>` 标签文本（strip 后）、URL path
4. 请求间隔 `--delay` 秒，设置合理 User-Agent
5. 请求失败（非 200、超时）跳过，不中断整体爬取

### 依赖

- `requests`（已在项目中使用）
- `beautifulsoup4`（新增，仅此脚本使用）
- `ruamel.yaml`（新增，保留 YAML 注释和格式的写入；若不可用 fallback 到 PyYAML 追加模式）

---

## 影响范围

| 文件 | 操作 |
|------|------|
| `tracking-setup-e2e/scripts/crawl_web_pages.py` | 新增 |
| `tracking-setup-e2e/requirements.txt`（若存在） | 新增 `beautifulsoup4`、`ruamel.yaml` |

不修改 `rule_engine.py`、`event_sequencer.py`、`PropertyEnumResolver`。

---

## 验收标准

- 运行脚本后输出包含 `$url`、`$title`、`$url_path` 三个键的 YAML 片段
- 所有 URL 属于起始 URL 的同域
- `--output` 模式不覆盖 `property_enums` 中已有的其他键
- 爬取深度和页面数上限生效
- 单个页面请求失败不中断整体爬取
