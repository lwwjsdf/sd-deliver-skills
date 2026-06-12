"""Tests for scan_jsonl.py."""
import json

from scan_jsonl import scan_jsonl


def _write_jsonl(tmp_path, records, filename="data.jsonl"):
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_scan_empty(tmp_path):
    path = _write_jsonl(tmp_path, [])
    result = scan_jsonl([path])
    assert result["total_rows"] == 0
    assert result["events"] == {}


def test_scan_tracks_and_profiles(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "Login", "distinct_id": "u1",
         "time": 1704067200000, "properties": {"platform": "MP"}},
        {"type": "track", "event": "Login", "distinct_id": "u1",
         "time": 1704067300000, "properties": {"platform": "Web"}},
        {"type": "profile_set", "distinct_id": "u1", "properties": {"level": "vip"}},
    ])
    result = scan_jsonl([path])
    assert result["total_rows"] == 3
    assert result["record_types"]["track"] == 2
    assert result["record_types"]["profile_set"] == 1
    assert result["events"]["Login"]["count"] == 2
    assert "platform" in result["events"]["Login"]["sample_properties"]
    assert result["users"]["distinct_id_count"] == 1


def test_scan_excludes_preset_events(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "$MPLaunch", "distinct_id": "u1",
         "time": 1704067200000, "properties": {"$scene": "1001"}},
        {"type": "track", "event": "Login", "distinct_id": "u1",
         "time": 1704067200000, "properties": {}},
    ])
    result = scan_jsonl([path], include_preset=False)
    assert "$MPLaunch" not in result["events"]
    assert "Login" in result["events"]


def test_scan_multiple_files(tmp_path):
    path1 = _write_jsonl(tmp_path, [
        {"type": "track", "event": "A", "distinct_id": "u1", "time": 1704067200000, "properties": {"x": 1}},
    ], filename="a.jsonl")
    path2 = _write_jsonl(tmp_path, [
        {"type": "track", "event": "B", "distinct_id": "u2", "time": 1704067200000, "properties": {"y": 2}},
    ], filename="b.jsonl")
    result = scan_jsonl([path1, path2])
    assert result["total_rows"] == 2
    assert "A" in result["events"]
    assert "B" in result["events"]
    assert result["events"]["A"]["count"] == 1
    assert result["events"]["B"]["count"] == 1


def test_scan_sample_size(tmp_path):
    records = [
        {"type": "track", "event": "Login", "distinct_id": f"u{i}",
         "time": 1704067200000 + i * 1000, "properties": {"idx": i}}
        for i in range(100)
    ]
    path = _write_jsonl(tmp_path, records)
    result = scan_jsonl([path], sample_size=10)
    # total_rows counts all, but property samples limited
    assert result["total_rows"] == 100
    assert result["events"]["Login"]["count"] == 100
    # sample logic: after sample exceeded, we still count but don't sample props
    # so prop sample may be empty or have some values depending on order
    assert "idx" in result["events"]["Login"]["sample_properties"]
