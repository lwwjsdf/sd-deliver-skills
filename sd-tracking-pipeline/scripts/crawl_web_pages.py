"""
crawl_web_pages.py — Crawl a website and output property_enums YAML for $url/$title/$url_path.

Usage:
    python3 scripts/crawl_web_pages.py --url https://www.westk.hk/tc/home
    python3 scripts/crawl_web_pages.py --url https://www.westk.hk/tc/home \
        --output rules/special/westk/business_logic.yaml --depth 2 --max-pages 50

Dependencies:
    pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections import deque
from datetime import date
from typing import List
from urllib.parse import urljoin, urlparse

# ── Dependency check & auto-install ───────────────────────────────────────────


def _ensure_dependencies():
    """Ensure required packages are installed."""
    missing = []
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append("beautifulsoup4")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            print(f"Please run manually: pip install {' '.join(missing)}")
            sys.exit(1)


_ensure_dependencies()

import requests
from bs4 import BeautifulSoup

_SKIP_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".docx",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".mp4",
    ".mp3",
    ".woff",
    ".woff2",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; crawl_web_pages/1.0; "
        "+https://github.com/anthropics/claude-code)"
    )
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedupe(seq: list) -> list:
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


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

        # Normalise: strip fragment, keep unstripped copy for urljoin
        url_for_join = url.split("#")[0]
        url = url_for_join.rstrip("/") or url_for_join
        if url in visited:
            continue
        visited.add(url)

        if _should_skip(url):
            continue

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        title = " ".join(title_tag.get_text().split()) if title_tag else ""
        path = urlparse(url).path

        pages.append({"url": url, "title": title, "path": path})
        print(f"  [{len(pages):3d}] {url}", file=sys.stderr)

        if depth < max_depth:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith("javascript:"):
                    continue
                abs_url = urljoin(url_for_join, href).split("#")[0].rstrip("/")
                parsed_abs = urlparse(abs_url)
                if (
                    parsed_abs.scheme in {"http", "https"}
                    and _is_internal(base_netloc, abs_url)
                    and abs_url not in visited
                ):
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
    titles = _dedupe([p["title"] for p in pages if p["title"]])
    paths = _dedupe([p["path"] for p in pages])

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
    Replace $url/$title/$url_path in the property_enums block of yaml_path.
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
    pe["$url"] = _dedupe([p["url"] for p in pages])
    pe["$title"] = _dedupe([p["title"] for p in pages if p["title"]])
    pe["$url_path"] = _dedupe([p["path"] for p in pages])

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
    parser.add_argument(
        "--depth", type=int, default=2, help="BFS max depth (default: 2)"
    )
    parser.add_argument(
        "--max-pages", type=int, default=50, help="Max pages to crawl (default: 50)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="YAML file to merge results into (default: print to stdout)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    args = parser.parse_args()

    print(
        f"Crawling {args.url} (depth={args.depth}, max-pages={args.max_pages}) ...",
        file=sys.stderr,
    )
    pages = crawl(
        args.url, max_depth=args.depth, max_pages=args.max_pages, delay=args.delay
    )
    print(f"Found {len(pages)} pages.", file=sys.stderr)

    if not pages:
        print(
            "No pages found. Check the URL and network connectivity.", file=sys.stderr
        )
        sys.exit(1)

    if args.output:
        _merge_into_yaml(args.output, pages, args.url)
        print("Done.", file=sys.stderr)
    else:
        print(_build_yaml_fragment(pages, args.url))


if __name__ == "__main__":
    main()
