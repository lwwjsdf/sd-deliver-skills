"""Tests for crawl_web_pages.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from crawl_web_pages import _dedupe, _is_internal, _should_skip, crawl, _build_yaml_fragment


def test_dedupe_preserves_order():
    assert _dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_is_internal_same_netloc():
    assert _is_internal("www.example.com", "https://www.example.com/page") is True


def test_is_internal_relative_url():
    assert _is_internal("www.example.com", "/page") is True


def test_is_internal_external_url():
    assert _is_internal("www.example.com", "https://other.com/page") is False


def test_should_skip_binary_files():
    assert _should_skip("https://example.com/file.pdf") is True
    assert _should_skip("https://example.com/file.png") is True


def test_should_skip_html():
    assert _should_skip("https://example.com/page.html") is False
    assert _should_skip("https://example.com/page") is False


@patch("crawl_web_pages.requests.get")
def test_crawl_follows_internal_links(mock_get):
    home_html = '''
    <html><head><title>Home</title></head>
    <body><a href="/page1">Page 1</a><a href="https://example.com/page2">Page 2</a></body></html>
    '''
    page1_html = '<html><head><title>Page 1</title></head><body></body></html>'
    page2_html = '<html><head><title>Page 2</title></head><body></body></html>'

    def side_effect(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if url.endswith("/page1"):
            resp.text = page1_html
        elif url.endswith("/page2"):
            resp.text = page2_html
        else:
            resp.text = home_html
        return resp

    mock_get.side_effect = side_effect

    pages = crawl("https://example.com/", max_depth=1, max_pages=10, delay=0)
    urls = {p["url"] for p in pages}
    assert "https://example.com" in urls
    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls


@patch("crawl_web_pages.requests.get")
def test_crawl_skips_non_200(mock_get):
    resp = MagicMock()
    resp.status_code = 404
    mock_get.return_value = resp

    pages = crawl("https://example.com/", max_depth=1, max_pages=10, delay=0)
    assert pages == []


@patch("crawl_web_pages.requests.get")
def test_crawl_respects_max_pages(mock_get):
    home_html = '<html><head><title>Home</title></head><body>'
    for i in range(20):
        home_html += f'<a href="/page{i}">Page {i}</a>'
    home_html += '</body></html>'

    def side_effect(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if url in ("https://example.com", "https://example.com/"):
            resp.text = home_html
        else:
            resp.text = f'<html><head><title>{url}</title></head><body></body></html>'
        return resp

    mock_get.side_effect = side_effect

    pages = crawl("https://example.com/", max_depth=1, max_pages=5, delay=0)
    assert len(pages) == 5


def test_build_yaml_fragment():
    pages = [
        {"url": "https://example.com/", "title": "Home", "path": "/"},
        {"url": "https://example.com/page1", "title": 'Page "One"', "path": "/page1"},
    ]
    yaml_text = _build_yaml_fragment(pages, "https://example.com/")
    assert "$url:" in yaml_text
    assert "$title:" in yaml_text
    assert "$url_path:" in yaml_text
    assert 'https://example.com/' in yaml_text
    assert 'Page \\"One\\"' in yaml_text


def test_build_yaml_fragment_dedupes_titles():
    pages = [
        {"url": "https://example.com/", "title": "Home", "path": "/"},
        {"url": "https://example.com/page1", "title": "Home", "path": "/page1"},
    ]
    yaml_text = _build_yaml_fragment(pages, "https://example.com/")
    assert yaml_text.count('"Home"') == 1


@patch("ruamel.yaml.YAML")
def test_merge_into_yaml_updates_keys(mock_yaml_cls, tmp_path):
    yaml_path = tmp_path / "business_logic.yaml"
    yaml_path.write_text("meta:\n  project: demo\n", encoding="utf-8")

    pages = [{"url": "https://example.com/", "title": "Home", "path": "/"}]
    from crawl_web_pages import _merge_into_yaml
    _merge_into_yaml(str(yaml_path), pages, "https://example.com/")

    mock_instance = mock_yaml_cls.return_value
    assert mock_instance.load.called
    assert mock_instance.dump.called
