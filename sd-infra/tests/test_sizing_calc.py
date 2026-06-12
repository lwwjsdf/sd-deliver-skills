"""Tests for sizing_calc.py."""
import pytest

from sizing_calc import parse_count, wan_to_yi, ceil_to_standard_disk


@pytest.mark.parametrize("input_str,expected", [
    ("5000万", 5000),
    ("1.5亿", 15000),
    ("3亿", 30000),
    ("500", 500),
    ("1,000万", 1000),
    ("1，000万", 1000),
])
def test_parse_count(input_str, expected):
    assert parse_count(input_str) == expected


def test_parse_count_invalid():
    with pytest.raises(ValueError):
        parse_count("invalid")


@pytest.mark.parametrize("value,expected", [
    (5000, "5000万"),
    (15000, "1.50亿"),
    (100000, "10.00亿"),
    (500, "500万"),
])
def test_wan_to_yi(value, expected):
    assert wan_to_yi(value) == expected


@pytest.mark.parametrize("size_gb,expected", [
    (100, 500),
    (500, 500),
    (800, 1000),
    (1500, 1500),
    (5000, 5000),
    (12000, 12000),
])
def test_ceil_to_standard_disk(size_gb, expected):
    assert ceil_to_standard_disk(size_gb) == expected
