"""Tests for mock_data_manager.py."""
import sys
from pathlib import Path

import pytest

from mock_data_manager import (
    get_mock_data_dir,
    scan_mock_data,
    human_readable_size,
    backup_mock_data,
    clean_mock_data,
    main,
)


def test_get_mock_data_dir():
    assert get_mock_data_dir("/tmp/proj") == Path("/tmp/proj/mock_data")
    assert get_mock_data_dir(".") == Path("./mock_data")


def test_human_readable_size():
    assert human_readable_size(0) == "0 B"
    assert human_readable_size(512) == "512.0 B"
    assert human_readable_size(1024) == "1.0 KB"
    assert human_readable_size(1024 * 1024) == "1.0 MB"


def test_scan_mock_data_nonexistent(tmp_path):
    stats = scan_mock_data(str(tmp_path))
    assert stats["exists"] is False
    assert stats["count"] == 0


def test_scan_mock_data_existing(tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "a.jsonl").write_text("x" * 100)
    (mock_dir / "b.json").write_text("y" * 50)
    stats = scan_mock_data(str(tmp_path))
    assert stats["exists"] is True
    assert stats["count"] == 2
    assert stats["total_size"] == 150
    assert stats["files"][0]["name"] == "a.jsonl"  # sorted by size desc


def test_clean_mock_data_keeps_final_jsonl(tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "westk.jsonl").write_text("data")
    (mock_dir / "westk_part_1.jsonl").write_text("part")
    (mock_dir / "tmp.txt").write_text("tmp")
    clean_mock_data(str(tmp_path), keep_final=True)
    assert (mock_dir / "westk.jsonl").exists()
    assert not (mock_dir / "tmp.txt").exists()
    assert not (mock_dir / "westk_part_1.jsonl").exists()


def test_clean_mock_data_removes_all(tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "westk.jsonl").write_text("data")
    clean_mock_data(str(tmp_path), keep_final=False)
    assert not (mock_dir / "westk.jsonl").exists()


def test_backup_mock_data_moves_files(tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "data.jsonl").write_text("data")
    backup_mock_data(str(tmp_path), compress=False)
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    backup_dir = mock_dir / "backup" / today
    assert backup_dir.exists()
    assert (backup_dir / "data.jsonl").exists()
    assert not (mock_dir / "data.jsonl").exists()


def test_backup_mock_data_no_files(tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    result = backup_mock_data(str(tmp_path), compress=False)
    assert result == ""


def test_main_scan(capsys, tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "data.jsonl").write_text("data")
    sys.argv = ["mock_data_manager.py", "scan", str(tmp_path)]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "mock_data/ 扫描结果" in captured.out
    assert "data.jsonl" in captured.out


def test_main_clean(capsys, tmp_path):
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    (mock_dir / "tmp.txt").write_text("tmp")
    sys.argv = ["mock_data_manager.py", "clean", str(tmp_path)]
    main()
    captured = capsys.readouterr()
    assert "已清理" in captured.out
    assert not (mock_dir / "tmp.txt").exists()
