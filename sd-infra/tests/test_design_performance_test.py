"""Tests for design_performance_test.py."""
from pathlib import Path

import openpyxl
import pytest

from design_performance_test import generate_word_report, generate_excel_report


def test_generate_excel_report(tmp_path):
    out = tmp_path / "perf.xlsx"
    path = generate_excel_report(
        output_path=str(out),
        dau=1_000_000,
        daily_events=5_000_000,
        retention_days=365,
        cloud="AWS",
        region="ap-southeast-1",
        include_cdp=True,
        include_ma=True,
    )
    assert path == str(out)
    assert out.exists()

    wb = openpyxl.load_workbook(out, data_only=True)
    assert "Scope" in wb.sheetnames
    assert "Environment" in wb.sheetnames
    assert "Assumptions" in wb.sheetnames
    assert "Schedule" in wb.sheetnames

    ws = wb["Scope"]
    headers = [cell.value for cell in ws[1]]
    assert "Scenario" in headers


def test_generate_word_report(tmp_path):
    out = tmp_path / "perf.docx"
    path = generate_word_report(
        output_path=str(out),
        dau=1_000_000,
        daily_events=5_000_000,
        retention_days=365,
        cloud="AWS",
        region="ap-southeast-1",
        include_cdp=True,
        include_ma=True,
    )
    assert path == str(out)
    assert out.exists()

    from docx import Document
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert any("Performance Test Plan" in t for t in texts)
    assert any("Scope of Testing" in t for t in texts)


def test_generate_excel_report_products(tmp_path):
    out = tmp_path / "perf.xlsx"
    generate_excel_report(
        output_path=str(out),
        dau=100_000,
        daily_events=500_000,
        retention_days=180,
        cloud="Azure",
        region="eastasia",
        include_cdp=True,
        include_ma=False,
    )
    wb = openpyxl.load_workbook(out, data_only=True)
    ws = wb["Environment"]
    values = []
    for row in ws.iter_rows(values_only=True):
        values.extend(row)
    assert "Azure" in values
    assert "eastasia" in values
    assert "CDP" in values
