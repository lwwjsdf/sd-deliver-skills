#!/usr/bin/env python3
"""
mock_data_manager.py — 管理 mock_data/ 目录的历史数据

功能：
  scan    — 扫描目录，统计文件数量和大小
  backup  — 备份历史文件到 mock_data/backup/YYYYMMDD/
  clean   — 清理历史文件（可选保留最终 jsonl）
  report  — 生成扫描报告

用法：
  python3 mock_data_manager.py scan [project_dir]
  python3 mock_data_manager.py backup [project_dir] [--compress]
  python3 mock_data_manager.py clean [project_dir] [--keep-final]
  python3 mock_data_manager.py report [project_dir]
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def get_mock_data_dir(project_dir: str = ".") -> Path:
    """Return mock_data/ path."""
    return Path(project_dir) / "mock_data"


def scan_mock_data(project_dir: str = ".") -> dict:
    """Scan mock_data/ and return statistics."""
    mock_dir = get_mock_data_dir(project_dir)
    if not mock_dir.exists():
        return {"exists": False, "files": [], "total_size": 0, "count": 0}

    files = []
    total_size = 0
    for f in mock_dir.iterdir():
        if f.is_file():
            size = f.stat().st_size
            files.append({
                "name": f.name,
                "size": size,
                "size_human": human_readable_size(size)
            })
            total_size += size

    # Sort by size desc
    files.sort(key=lambda x: x["size"], reverse=True)

    return {
        "exists": True,
        "path": str(mock_dir),
        "files": files,
        "count": len(files),
        "total_size": total_size,
        "total_size_human": human_readable_size(total_size)
    }


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def print_scan_report(stats: dict):
    """Print formatted scan report."""
    if not stats["exists"]:
        print("mock_data/ 目录不存在")
        return

    print(f"\n📦 mock_data/ 扫描结果")
    print(f"   路径: {stats['path']}")
    print(f"   文件数: {stats['count']}")
    print(f"   总大小: {stats['total_size_human']}")
    print(f"\n   文件列表:")
    for f in stats["files"]:
        print(f"     {f['name']:40s} {f['size_human']:>10s}")
    print()


def backup_mock_data(project_dir: str = ".", compress: bool = True) -> str:
    """Backup mock_data/ files to backup/YYYYMMDD/ directory."""
    mock_dir = get_mock_data_dir(project_dir)
    if not mock_dir.exists():
        print("mock_data/ 目录不存在，无需备份")
        return ""

    # Check if there are files to backup (exclude backup/ dir)
    files_to_backup = [f for f in mock_dir.iterdir() if f.is_file()]
    if not files_to_backup:
        print("mock_data/ 中没有文件，无需备份")
        return ""

    # Create backup directory
    today = datetime.now().strftime("%Y%m%d")
    backup_dir = mock_dir / "backup" / today
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Move files
    moved_count = 0
    for f in files_to_backup:
        dest = backup_dir / f.name
        shutil.move(str(f), str(dest))
        moved_count += 1

    print(f"✅ 已备份 {moved_count} 个文件到 {backup_dir}")

    # Compress if requested
    if compress and moved_count > 0:
        tar_path = mock_dir / "backup" / f"{today}.tar.gz"
        import subprocess
        result = subprocess.run(
            ["tar", "czf", str(tar_path), "-C", str(mock_dir / "backup"), today],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Remove uncompressed backup dir
            shutil.rmtree(backup_dir)
            print(f"✅ 已压缩为 {tar_path}")
            return str(tar_path)
        else:
            print(f"⚠️ 压缩失败: {result.stderr}")
            return str(backup_dir)

    return str(backup_dir)


def clean_mock_data(project_dir: str = ".", keep_final: bool = True):
    """Clean mock_data/ files."""
    mock_dir = get_mock_data_dir(project_dir)
    if not mock_dir.exists():
        print("mock_data/ 目录不存在，无需清理")
        return

    removed = []
    kept = []

    for f in mock_dir.iterdir():
        if not f.is_file():
            continue

        if keep_final and f.suffix == ".jsonl" and "_part_" not in f.name:
            # Keep final jsonl files (e.g., westk.jsonl)
            kept.append(f.name)
            continue

        f.unlink()
        removed.append(f.name)

    print(f"✅ 已清理 {len(removed)} 个文件")
    if kept:
        print(f"📦 保留 {len(kept)} 个最终 jsonl 文件:")
        for name in kept:
            print(f"     {name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="管理 mock_data/ 目录的历史数据"
    )
    parser.add_argument(
        "action",
        choices=["scan", "backup", "clean", "report"],
        help="操作类型"
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="项目目录（默认当前目录）"
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="backup 时压缩为 tar.gz"
    )
    parser.add_argument(
        "--keep-final",
        action="store_true",
        default=True,
        help="clean 时保留最终 jsonl 文件"
    )
    parser.add_argument(
        "--remove-all",
        action="store_true",
        help="clean 时删除所有文件（包括最终 jsonl）"
    )

    args = parser.parse_args()

    if args.action == "scan" or args.action == "report":
        stats = scan_mock_data(args.project_dir)
        print_scan_report(stats)
        # Return exit code 1 if files exist (for shell scripting)
        sys.exit(0 if stats["exists"] and stats["count"] > 0 else 0)

    elif args.action == "backup":
        backup_path = backup_mock_data(args.project_dir, compress=args.compress)
        if backup_path:
            print(f"备份位置: {backup_path}")

    elif args.action == "clean":
        keep_final = not args.remove_all
        clean_mock_data(args.project_dir, keep_final=keep_final)


if __name__ == "__main__":
    main()
