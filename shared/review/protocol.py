"""
Review Framework 核心协议

所有 skill 的 checker / fixer 都实现这套接口。
Checker 是纯函数（不修改任何文件）。
Fixer 修改源文件，返回是否成功。
ReviewLoop 驱动循环直到满足终止条件。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ── 基础类型 ──────────────────────────────────────────────────────────────────

class Severity(Enum):
    FAIL = "FAIL"    # 必须修复，否则产物不可用
    WARN = "WARN"    # 建议修复，但可以接受
    INFO = "INFO"    # 仅供参考，不影响通过

    @property
    def icon(self) -> str:
        return {"FAIL": "✗", "WARN": "⚠", "INFO": "ℹ"}[self.value]

    def __gt__(self, other: "Severity") -> bool:
        order = {Severity.INFO: 0, Severity.WARN: 1, Severity.FAIL: 2}
        return order[self] > order[other]


@dataclass
class Issue:
    """单条检查问题。"""
    severity:     Severity
    checker:      str          # checker 的名称，如 "overlap_checker"
    category:     str          # 问题类别，如 "visual" / "semantic" / "completeness"
    message:      str          # 问题描述（人类可读）
    location:     str = ""     # 问题位置，如 "node:cdp" / "edge:crm->cdp" / "cell:B3"
    auto_fixable: bool = False # 是否有对应的 fixer 可以自动修复
    fix_hint:     str = ""     # 给 fixer 或用户的修复建议

    def __str__(self) -> str:
        loc = f" @ {self.location}" if self.location else ""
        fix = f"  → {self.fix_hint}" if self.fix_hint else ""
        return f"  {self.severity.icon} [{self.checker}]{loc}: {self.message}{fix}"


@dataclass
class CheckResult:
    """单个 checker 的检查结果。"""
    checker_name: str
    passed:       bool
    issues:       list[Issue] = field(default_factory=list)
    duration_ms:  float = 0.0

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARN)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (f"[{status}] {self.checker_name}"
                f"  {self.fail_count} fail, {self.warn_count} warn"
                f"  ({self.duration_ms:.0f}ms)")


# ── 抽象接口 ──────────────────────────────────────────────────────────────────

class Checker(ABC):
    """
    Checker 接口。纯函数，不修改任何文件。
    子类实现 check() 方法，返回 CheckResult。

    context 是传递给 checker 的上下文数据，由各 skill 自定义。
    对于 draw-diagram：context = {"arch": {...}, "drawio_path": "..."}
    对于 server-sizing：context = {"calc_result": {...}, "config": {...}}
    对于 excel 生成：context = {"workbook_path": "...", "spec": {...}}
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """checker 的唯一名称。"""

    @property
    @abstractmethod
    def category(self) -> str:
        """检查类别：visual / semantic / completeness / spec_compliance。"""

    @abstractmethod
    def check(self, context: dict[str, Any]) -> CheckResult:
        """执行检查，返回结果。不得修改 context 或任何文件。"""

    def run(self, context: dict[str, Any]) -> CheckResult:
        """执行 check() 并计时，捕获异常。"""
        t0 = time.perf_counter()
        try:
            result = self.check(context)
        except Exception as e:
            result = CheckResult(
                checker_name=self.name,
                passed=False,
                issues=[Issue(
                    severity=Severity.FAIL,
                    checker=self.name,
                    category=self.category,
                    message=f"Checker 内部错误: {e}",
                    auto_fixable=False,
                )],
            )
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result


class Fixer(ABC):
    """
    Fixer 接口。接收包含 FAIL issue 的 CheckResult，尝试自动修复。
    修复的目标是源文件（arch.yaml / excel / calc 配置），而不是产物。

    fix() 返回 (success, message)。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """fixer 的唯一名称，与对应 checker 同名。"""

    @abstractmethod
    def fix(self, issues: list[Issue], context: dict[str, Any]) -> tuple[bool, str]:
        """
        尝试修复 issues。
        - 修改 context 中的源数据（如 arch dict）
        - 将修改写回文件
        返回 (全部修复成功, 修复摘要)
        """


# ── Review Report ─────────────────────────────────────────────────────────────

@dataclass
class ReviewReport:
    """一轮 review 的完整报告。"""
    round_num:      int
    results:        list[CheckResult] = field(default_factory=list)
    fixes_applied:  list[str] = field(default_factory=list)
    fixes_pending:  list[Issue] = field(default_factory=list)   # 无法自动修复，需人工
    timestamp:      float = field(default_factory=time.time)

    @property
    def total_fail(self) -> int:
        return sum(r.fail_count for r in self.results)

    @property
    def total_warn(self) -> int:
        return sum(r.warn_count for r in self.results)

    @property
    def passed(self) -> bool:
        """无 FAIL 即通过（WARN 可接受）。"""
        return self.total_fail == 0

    def print(self, verbose: bool = False):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        print(f"\n{'='*60}")
        print(f"Review Round {self.round_num}  {status}")
        print(f"{'='*60}")
        for r in self.results:
            print(f"  {r.summary()}")
            if verbose or not r.passed:
                for issue in r.issues:
                    print(issue)
            elif r.warn_count:
                for issue in r.issues:
                    print(issue)
        if self.fixes_applied:
            print(f"\n✓ 自动修复 ({len(self.fixes_applied)}):")
            for f in self.fixes_applied:
                print(f"    {f}")
        if self.fixes_pending:
            print(f"\n⚠ 需人工确认 ({len(self.fixes_pending)}):")
            for i in self.fixes_pending:
                print(f"    {i}")
        print(f"\nFAIL: {self.total_fail}  WARN: {self.total_warn}")


# ── Review Loop ───────────────────────────────────────────────────────────────

class ReviewLoop:
    """
    驱动 generate → check → fix → loop 循环。

    用法：
        loop = ReviewLoop(
            checkers=[OverlapChecker(), PiiColorChecker(), ...],
            fixers={"overlap_checker": OverlapFixer(), ...},
            max_rounds=5,
        )
        final_report = loop.run(
            generate_fn=lambda: render(arch, output_path),
            context={"arch": arch, "drawio_path": output_path},
        )
    """

    def __init__(
        self,
        checkers: list[Checker],
        fixers: dict[str, Fixer] | None = None,
        max_rounds: int = 5,
        stop_on_pass: bool = True,    # PASS 后立即停止
        require_human_for_semantic: bool = True,  # 语义类问题需要人工确认
    ):
        self.checkers   = checkers
        self.fixers     = fixers or {}
        self.max_rounds = max_rounds
        self.stop_on_pass = stop_on_pass
        self.require_human_for_semantic = require_human_for_semantic
        self.history: list[ReviewReport] = []

    def run(
        self,
        generate_fn,               # callable：生成/重新生成产物
        context: dict[str, Any],
        human_confirm_fn=None,     # callable(issues) → bool：人工确认接口（可选）
        verbose: bool = True,
    ) -> ReviewReport:
        """
        执行 review 循环。
        返回最后一轮的 ReviewReport。
        """
        for round_num in range(1, self.max_rounds + 1):
            # 1. 生成/重新生成产物
            print(f"\n{'─'*40}")
            print(f"Round {round_num}/{self.max_rounds}: generating...")
            generate_fn()

            # 2. 执行所有 checker
            results = [checker.run(context) for checker in self.checkers]

            report = ReviewReport(round_num=round_num, results=results)

            # 3. 收集 FAIL issues
            fail_issues = [
                issue
                for r in results
                for issue in r.issues
                if issue.severity == Severity.FAIL
            ]

            # 4. 分类：可自动修复 vs 需人工确认
            auto_fixable   = [i for i in fail_issues if i.auto_fixable]
            needs_human    = [i for i in fail_issues if not i.auto_fixable]

            # 语义类问题即使标记为 auto_fixable，也需要人工确认
            if self.require_human_for_semantic:
                semantic = [i for i in auto_fixable if i.category == "semantic"]
                auto_fixable  = [i for i in auto_fixable if i.category != "semantic"]
                needs_human  += semantic

            # 5. 执行自动修复
            if auto_fixable:
                applied = self._apply_fixes(auto_fixable, context)
                report.fixes_applied = applied

            # 6. 人工确认（如有）
            if needs_human and human_confirm_fn:
                confirmed = human_confirm_fn(needs_human)
                if confirmed:
                    # 用户确认后执行 fixer（即使是语义类）
                    extra = self._apply_fixes(needs_human, context, force=True)
                    report.fixes_applied += extra
                    report.fixes_pending = []
                else:
                    report.fixes_pending = needs_human
            else:
                report.fixes_pending = needs_human

            # 7. 打印报告
            if verbose:
                report.print()

            self.history.append(report)

            # 8. 终止条件
            if report.passed and self.stop_on_pass:
                print(f"\n✅ Review passed in {round_num} round(s).")
                return report

            if not auto_fixable and not (needs_human and human_confirm_fn):
                # 没有可修复的问题，继续也没意义
                if not report.passed:
                    print(f"\n⚠ Round {round_num}: {len(needs_human)} issue(s) need human review.")
                    return report

        # 达到最大轮次
        last = self.history[-1]
        if not last.passed:
            print(f"\n⚠ Max rounds ({self.max_rounds}) reached. "
                  f"Remaining: {last.total_fail} FAIL, {last.total_warn} WARN.")
        return last

    def _apply_fixes(
        self, issues: list[Issue], context: dict, force: bool = False
    ) -> list[str]:
        """按 issue.checker 分组，调用对应 fixer。"""
        applied = []
        by_checker: dict[str, list[Issue]] = {}
        for issue in issues:
            by_checker.setdefault(issue.checker, []).append(issue)

        for checker_name, checker_issues in by_checker.items():
            fixer = self.fixers.get(checker_name)
            if not fixer:
                continue
            success, msg = fixer.fix(checker_issues, context)
            if success:
                applied.append(f"{checker_name}: {msg}")
            else:
                applied.append(f"{checker_name}: fix attempted but failed — {msg}")

        return applied
