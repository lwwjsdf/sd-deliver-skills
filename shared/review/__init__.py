"""
sdeliver Review Framework
通用的 generate → check → fix → loop 机制，被所有 skill 使用。
"""
from .protocol import (
    Issue, Severity, CheckResult, Checker, Fixer,
    ReviewReport, ReviewLoop
)

__all__ = [
    "Issue", "Severity", "CheckResult", "Checker", "Fixer",
    "ReviewReport", "ReviewLoop",
]
