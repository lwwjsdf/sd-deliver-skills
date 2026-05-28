# Web Page Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `crawl_web_pages.py`，爬取指定网站的内部页面，输出兼容 `property_enums` 的 YAML 片段，供 Web 端造数使用。

**Architecture:** 单文件脚本，BFS 爬取同域链接，提取 URL + `<title>`，输出到 stdout 或合并写入 `business_logic.yaml` 的 `property_enums` 区块（用 `ruamel.yaml` 保留注释和格式）。不修改任何现有文件。

**Tech Stack:** Python 3.x, requests, beautifulsoup4, ruamel.yaml, argparse

---

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `tracking-setup-e2e/scripts/crawl_web_pages.py` | 新增 |

---

### Task 1: 实现 crawl_web_pages.py

**Files:**
- Create: `tracking-setup-e2e/scripts/crawl_web_pages.py`

- [ ] **Step 1: 验证依赖已安装**

```bash
python3 -c "import requests, bs4, ruamel.yaml; print('deps OK')"
```

期望输出：`deps OK`

- [ ] **Step 2: 创建脚本文件**

创建 `tracking-setup-e2e/scripts/crawl_web_pages.py`，完整内容如下：

```python
"""
crawl_web_pages.py — Crawl a website and output property_enums YAML for $url/$title/$url_path.

Usage:
    python3 scripts/crawl_web_pages.py --url https://www.westk.hk/tc/home
    python3 scripts/crawl_web_pages.py --url https://www.westk.hk/tc/home \
        --output rules/special/westk/business_logic.yaml --depth 2 --max-pages 50
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_SKIP_EXTENSIONS = {
    ".pdf", ".zip", ".docx", ".xlsx", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".ico", ".mp4", ".mp3", ".woff", ".woff2",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; crawl_web_pages/1.0; "
        "+https://github.com/anthropics/claude-code)"
    )
}


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


def _is_internal(base_netloc: str, url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == base_netloc or parsed.netloc == ""


def _should_skip(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _SKIP_EXTENSIONS)


def crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    delay: float = 0.5,
) -> List[dict]:
    """
    BFS crawl from start_url. Returns list of {url, title, path} dicts.
    Skips non-200 responses and file downloads silently.
    """
    parsed_start = urlparse(start_url)
    base_netloc = parsed_start.netloc

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    pages: List[dict] = []

    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()

        # Normalise: strip fragment
        url = url.split("#")[0].rstrip("/") or url
        if url in visited:
            continue
        visited.add(url)

        if _should_skip(url):
            continue

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
        except requests.RequestException:
            continue

        if resp.status_code != 200:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        path = urlparse(url).path

        pages.append({"url": url, "title": title, "path": path})
        print(f"  [{len(pages):3d}] {url}", file=sys.stderr)

        if depth < max_depth:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith("javascript:"):
                    continue
                abs_url = urljoin(url, href).split("#")[0].rstrip("/")
                if _is_internal(base_netloc, abs_url) and abs_url not in visited:
                    queue.append((abs_url, depth + 1))

        if delay > 0:
            time.sleep(delay)

    return pages


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------


def _build_yaml_fragment(pages: List[dict], start_url: str) -> str:
    """Return a YAML string with $url, $title, $url_path lists."""
    urls = [p["url"] for p in pages]
    titles = [p["title"] for p in pages if p["title"]]
    paths = [p["path"] for p in pages]

    lines = [
        f"# 由 crawl_web_pages.py 生成，来源：{start_url}",
        f"# 生成时间：{date.today().isoformat()}",
        "$url:",
    ]
    for u in urls:
        lines.append(f'  - "{u}"')
    lines.append("$title:")
    for t in titles:
        escaped = t.replace('"', '\\"')
        lines.append(f'  - "{escaped}"')
    lines.append("$url_path:")
    for p in paths:
        lines.append(f'  - "{p}"')

    return "\n".join(lines) + "\n"


def _merge_into_yaml(yaml_path: str, pages: List[dict], start_url: str) -> None:
    """
    Merge $url/$title/$url_path into the property_enums block of yaml_path.
    Uses ruamel.yaml to preserve comments and formatting.
    Only updates the three web keys; all other keys are untouched.
    """
    from ruamel.yaml import YAML

    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 120

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = ryaml.load(f)

    if data is None:
        data = {}

    if "property_enums" not in data or data["property_enums"] is None:
        data["property_enums"] = {}

    pe = data["property_enums"]
    pe["$url"] = [p["url"] for p in pages]
    pe["$title"] = [p["title"] for p in pages if p["title"]]
    pe["$url_path"] = [p["path"] for p in pages]

    keys_updated = ["$url", "$title", "$url_path"]
    print(f"Updating keys in property_enums: {keys_updated}", file=sys.stderr)
    print(f"Writing to: {yaml_path}", file=sys.stderr)

    with open(yaml_path, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl a website and output property_enums YAML for Web tracking."
    )
    parser.add_argument("--url", required=True, help="Starting URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="BFS max depth (default: 2)")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl (default: 50)")
    parser.add_argument("--output", default=None, help="YAML file to merge results into (default: print to stdout)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")
    args = parser.parse_args()

    print(f"Crawling {args.url} (depth={args.depth}, max-pages={args.max_pages}) ...", file=sys.stderr)
    pages = crawl(args.url, max_depth=args.depth, max_pages=args.max_pages, delay=args.delay)
    print(f"Found {len(pages)} pages.", file=sys.stderr)

    if not pages:
        print("No pages found. Check the URL and network connectivity.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        _merge_into_yaml(args.output, pages, args.url)
        print("Done.", file=sys.stderr)
    else:
        print(_build_yaml_fragment(pages, args.url))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 验证脚本语法正确**

```bash
cd tracking-setup-e2e && python3 -c "import ast; ast.parse(open('scripts/crawl_web_pages.py').read()); print('syntax OK')"
```

期望输出：`syntax OK`

- [ ] **Step 4: 验证 --help 正常输出**

```bash
cd tracking-setup-e2e && python3 scripts/crawl_web_pages.py --help
```

期望输出包含：`--url`, `--depth`, `--max-pages`, `--output`, `--delay`

- [ ] **Step 5: 用 mock HTTP server 验证爬取逻辑**

```bash
cd tracking-setup-e2e && python3 -c "
import sys
sys.path.insert(0, 'scripts')

# Patch requests.get to return mock HTML without hitting network
import requests
from unittest.mock import patch, MagicMock

HOME_HTML = '''<html><head><title>首頁 | 西九文化區</title></head>
<body>
  <a href='/tc/arts-culture'>Arts</a>
  <a href='/tc/whats-on'>Whats On</a>
  <a href='https://external.com/page'>External</a>
  <a href='#anchor'>Anchor</a>
  <a href='/tc/file.pdf'>PDF</a>
</body></html>'''

ARTS_HTML = '''<html><head><title>藝術及文化 | 西九文化區</title></head><body></body></html>'''
WHATSON_HTML = '''<html><head><title>節目及活動 | 西九文化區</title></head><body></body></html>'''

def mock_get(url, **kwargs):
    m = MagicMock()
    m.status_code = 200
    if 'arts-culture' in url:
        m.text = ARTS_HTML
    elif 'whats-on' in url:
        m.text = WHATSON_HTML
    else:
        m.text = HOME_HTML
    return m

from crawl_web_pages import crawl
with patch('requests.get', side_effect=mock_get):
    pages = crawl('https://www.westk.hk/tc/home', max_depth=1, max_pages=10, delay=0)

urls = [p['url'] for p in pages]
titles = [p['title'] for p in pages]

# Internal pages found
assert 'https://www.westk.hk/tc/home' in urls, f'Missing home: {urls}'
assert 'https://www.westk.hk/tc/arts-culture' in urls, f'Missing arts: {urls}'
assert 'https://www.westk.hk/tc/whats-on' in urls, f'Missing whats-on: {urls}'

# External and anchor links NOT followed
assert not any('external.com' in u for u in urls), f'External link leaked: {urls}'
assert not any('anchor' in u for u in urls), f'Anchor leaked: {urls}'

# PDF skipped
assert not any('.pdf' in u for u in urls), f'PDF leaked: {urls}'

# Titles extracted
assert '首頁 | 西九文化區' in titles, f'Missing title: {titles}'
assert '藝術及文化 | 西九文化區' in titles, f'Missing title: {titles}'

print('crawl() assertions passed.')
print('pages:', [(p[\"url\"], p[\"title\"]) for p in pages])
" && cd ..
```

期望输出：
```
crawl() assertions passed.
pages: [('https://www.westk.hk/tc/home', '首頁 | 西九文化區'), ...]
```

- [ ] **Step 6: 验证 YAML 片段输出格式**

```bash
cd tracking-setup-e2e && python3 -c "
import sys
sys.path.insert(0, 'scripts')
from crawl_web_pages import _build_yaml_fragment

pages = [
    {'url': 'https://www.westk.hk/tc/home', 'title': '首頁 | 西九文化區', 'path': '/tc/home'},
    {'url': 'https://www.westk.hk/tc/arts-culture', 'title': '藝術及文化 | 西九文化區', 'path': '/tc/arts-culture'},
]
fragment = _build_yaml_fragment(pages, 'https://www.westk.hk/tc/home')
print(fragment)

import yaml
parsed = yaml.safe_load(fragment.split('# 生成时间')[1].split('\n', 1)[1])
assert '\$url' not in str(parsed)  # keys are literal \$url
assert parsed['\$url'] == ['https://www.westk.hk/tc/home', 'https://www.westk.hk/tc/arts-culture']
assert parsed['\$title'] == ['首頁 | 西九文化區', '藝術及文化 | 西九文化區']
assert parsed['\$url_path'] == ['/tc/home', '/tc/arts-culture']
print('fragment assertions passed.')
" && cd ..
```

期望输出：YAML 片段内容 + `fragment assertions passed.`

- [ ] **Step 7: 验证 --output 合并写入不覆盖其他键**

```bash
cd tracking-setup-e2e && python3 -c "
import sys, tempfile, os
sys.path.insert(0, 'scripts')
from crawl_web_pages import _merge_into_yaml

# Create a temp YAML with existing property_enums
yaml_content = '''property_enums:
  seatArea:
    - Stalls
    - Balcony
  ticketType:
    - 标准票
    - 全馆通行票
'''

with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
    f.write(yaml_content)
    tmp_path = f.name

pages = [
    {'url': 'https://www.westk.hk/tc/home', 'title': '首頁 | 西九文化區', 'path': '/tc/home'},
]
_merge_into_yaml(tmp_path, pages, 'https://www.westk.hk/tc/home')

import yaml
with open(tmp_path) as f:
    result = yaml.safe_load(f)

pe = result['property_enums']
# Existing keys preserved
assert pe['seatArea'] == ['Stalls', 'Balcony'], f'seatArea overwritten: {pe}'
assert pe['ticketType'] == ['标准票', '全馆通行票'], f'ticketType overwritten: {pe}'
# New keys added
assert pe['\$url'] == ['https://www.westk.hk/tc/home'], f'Missing \$url: {pe}'
assert pe['\$title'] == ['首頁 | 西九文化區'], f'Missing \$title: {pe}'
assert pe['\$url_path'] == ['/tc/home'], f'Missing \$url_path: {pe}'

os.unlink(tmp_path)
print('merge assertions passed.')
" && cd ..
```

期望输出：`merge assertions passed.`

- [ ] **Step 8: 验证请求失败不中断爬取**

```bash
cd tracking-setup-e2e && python3 -c "
import sys
sys.path.insert(0, 'scripts')
from unittest.mock import patch, MagicMock
from crawl_web_pages import crawl

HOME_HTML = '''<html><head><title>Home</title></head>
<body><a href='/tc/ok'>OK</a><a href='/tc/fail'>Fail</a></body></html>'''
OK_HTML = '<html><head><title>OK Page</title></head><body></body></html>'

def mock_get(url, **kwargs):
    if 'fail' in url:
        raise Exception('connection error')
    m = MagicMock()
    m.status_code = 200
    m.text = OK_HTML if 'ok' in url else HOME_HTML
    return m

with patch('requests.get', side_effect=mock_get):
    pages = crawl('https://www.westk.hk/tc/home', max_depth=1, max_pages=10, delay=0)

urls = [p['url'] for p in pages]
assert 'https://www.westk.hk/tc/home' in urls
assert 'https://www.westk.hk/tc/ok' in urls
assert not any('fail' in u for u in urls)
print('failure-resilience assertions passed.')
" && cd ..
```

期望输出：`failure-resilience assertions passed.`

- [ ] **Step 9: Commit**

```bash
git add tracking-setup-e2e/scripts/crawl_web_pages.py
git commit -m "feat: add crawl_web_pages.py for Web property_enums generation"
```
