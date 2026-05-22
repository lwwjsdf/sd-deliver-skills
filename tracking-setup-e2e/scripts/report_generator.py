"""
report_generator.py — Generate a Markdown UAT validation report.

Depends on:
  - event_sequencer.py          : Event
  - fixed_account_generator.py  : User
  - constraint_validator.py     : Violation
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

from event_sequencer import Event
from fixed_account_generator import User
from constraint_validator import Violation


class ReportGenerator:
    def __init__(self, rule_engine, tracking_plan_path: str, output_dir: str):
        self.rule_engine = rule_engine
        self.tracking_plan_path = tracking_plan_path
        self.output_dir = output_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        users: List[User],
        events_by_user: Dict[str, List[Event]],
        violations_by_user: Dict[str, List[Violation]],
        id_violations: List[Violation],
    ) -> str:
        """生成 Markdown 报告，返回报告文件路径。"""
        os.makedirs(self.output_dir, exist_ok=True)
        report_path = os.path.join(self.output_dir, "uat_validation_report.md")

        lines: List[str] = []
        lines.extend(self._section_overview(users, events_by_user, violations_by_user))
        lines.extend(self._section_accounts(users, events_by_user, violations_by_user, id_violations))
        lines.extend(self._section_business_rules(users, violations_by_user))
        lines.extend(self._section_issues(violations_by_user, id_violations))

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return report_path

    # ------------------------------------------------------------------
    # Section 1: Overview
    # ------------------------------------------------------------------

    def _section_overview(
        self,
        users: List[User],
        events_by_user: Dict[str, List[Event]],
        violations_by_user: Dict[str, List[Violation]],
    ) -> List[str]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_events = sum(len(evs) for evs in events_by_user.values())
        passing_users = sum(
            1 for uid, viols in violations_by_user.items() if not viols
        )
        total_violations = sum(len(v) for v in violations_by_user.values())

        # Derive rule file path from rule_engine if possible
        meta = self.rule_engine.get_meta() if hasattr(self.rule_engine, "get_meta") else {}
        project = meta.get("project", "westk")
        rule_file = getattr(
            self.rule_engine,
            "_rule_path",
            f"rules/special/{project}/business_logic.yaml",
        )

        lines = [
            "# UAT 测试数据集验证报告",
            "",
            "## 1. 生成概览",
            f"- 生成时间: {now}",
            f"- 规则文件: {rule_file}",
            f"- 埋点方案: {self.tracking_plan_path}",
            "",
            "### 1.1 统计信息",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总用户数 | {len(users)} |",
            f"| 总事件数 | {total_events} |",
            f"| 通过验证用户 | {passing_users} |",
            f"| 违规数 | {total_violations} |",
            "",
        ]
        return lines

    # ------------------------------------------------------------------
    # Section 2: Fixed account validation
    # ------------------------------------------------------------------

    def _section_accounts(
        self,
        users: List[User],
        events_by_user: Dict[str, List[Event]],
        violations_by_user: Dict[str, List[Violation]],
        id_violations: List[Violation],
    ) -> List[str]:
        lines = [
            "## 2. 固定测试账号验证",
            "",
        ]

        # Group split users by account_id so we can render them together
        rendered_accounts: set = set()

        for idx, user in enumerate(users, start=1):
            account_id = user.account_id or user.user_id
            if account_id in rendered_accounts:
                continue
            rendered_accounts.add(account_id)

            # Collect all users belonging to this account
            account_users = [u for u in users if (u.account_id or u.user_id) == account_id]
            is_split = len(account_users) > 1

            lines.append(f"### 2.{idx} {account_id}")

            if is_split:
                # Special rendering for split-identity accounts (e.g. UAT-X07)
                lines.extend(self._render_split_account(account_users, id_violations))
            else:
                u = account_users[0]
                lines.extend(self._render_single_account(u, events_by_user, violations_by_user))

            lines.append("")

        return lines

    def _render_single_account(
        self,
        user: User,
        events_by_user: Dict[str, List[Event]],
        violations_by_user: Dict[str, List[Violation]],
    ) -> List[str]:
        lines: List[str] = []

        # Identity config
        lines.append("**身份配置**:")
        identity_order = ["crm_master_id", "email", "mobile", "unionid", "cookie_id"]
        for key in identity_order:
            val = user.identities.get(key)
            if val:
                lines.append(f"- {key}: {val}")
        # Any extra identities not in the standard order
        for key, val in user.identities.items():
            if key not in identity_order and val:
                lines.append(f"- {key}: {val}")
        lines.append("")

        # Event sequence
        events = events_by_user.get(user.user_id, [])
        lines.append(f"**事件序列** ({len(events)} events):")
        lines.append("| # | 事件 | 时间 | 状态 |")
        lines.append("|---|------|------|------|")
        for i, e in enumerate(events, start=1):
            ts = datetime.fromtimestamp(e.timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
            status = "✅" if e.is_success else "❌"
            lines.append(f"| {i} | {e.event_name} | {ts} | {status} |")
        lines.append("")

        # Constraint validation
        violations = violations_by_user.get(user.user_id, [])
        lines.append("**约束验证**:")
        if not violations:
            lines.append("- ✅ 无违规")
        else:
            for v in violations:
                detail = f" ({v.detail})" if v.detail else ""
                lines.append(f"- ❌ {v.description}{detail}")

        return lines

    def _render_split_account(
        self,
        account_users: List[User],
        id_violations: List[Violation],
    ) -> List[str]:
        lines: List[str] = []
        account_id = account_users[0].account_id or account_users[0].user_id

        sub_ids = ", ".join(u.user_id for u in account_users)
        lines.append(f"**预期**: 识别为 {len(account_users)} 个独立用户 ({sub_ids})")

        # Check if any id_violations involve these users
        user_ids = {u.user_id for u in account_users}
        relevant_violations = [
            v for v in id_violations if v.user_id in user_ids
        ]

        if not relevant_violations:
            lines.append("**ID Mapping 验证**: ✅ 两个用户无共享 identity")
        else:
            lines.append("**ID Mapping 验证**: ❌ 发现共享 identity")
            for v in relevant_violations:
                lines.append(f"- ❌ {v.description}")

        return lines

    # ------------------------------------------------------------------
    # Section 3: Business rule validation
    # ------------------------------------------------------------------

    def _section_business_rules(
        self,
        users: List[User],
        violations_by_user: Dict[str, List[Violation]],
    ) -> List[str]:
        lines = [
            "## 3. 业务规则验证",
            "",
        ]

        # Collect all violations across all users
        all_violations: List[Violation] = []
        for viols in violations_by_user.values():
            all_violations.extend(viols)

        def rule_status(constraint_type: str, description: str) -> str:
            matching = [
                v for v in all_violations
                if v.rule == constraint_type and v.description == description
            ]
            return "✅ 全部通过" if not matching else f"❌ {len(matching)} 个违规"

        # 3.1 Temporal order
        lines.append("### 3.1 时序约束")
        lines.append("| 规则 | 状态 |")
        lines.append("|------|------|")
        lines.append(f"| Registration 在 Login 前 | {rule_status('temporal_order', 'Registration 在 Login 前')} |")
        lines.append(f"| Login 在 Purchase 前 | {rule_status('temporal_order', 'Login 在 Purchase 前')} |")
        lines.append("")

        # 3.2 Field consistency
        lines.append("### 3.2 字段一致性")
        lines.append("| 规则 | 状态 |")
        lines.append("|------|------|")
        lines.append(f"| 票数明细数量等于订单票数 | {rule_status('field_consistency', '票数明细数量等于订单票数')} |")
        lines.append(f"| 明细金额之和不超过订单金额 | {rule_status('field_consistency', '明细金额之和不超过订单金额')} |")
        lines.append("")

        # 3.3 Business rules
        lines.append("### 3.3 业务规则")
        lines.append("| 规则 | 状态 |")
        lines.append("|------|------|")
        lines.append(f"| Admission 后不可 Refund | {rule_status('business_rule', 'Admission 后不可 Refund')} |")
        lines.append(f"| Voucher 场景严格互斥 | {rule_status('business_rule', 'Voucher 场景严格互斥')} |")
        lines.append("")

        return lines

    # ------------------------------------------------------------------
    # Section 4: Issues summary
    # ------------------------------------------------------------------

    def _section_issues(
        self,
        violations_by_user: Dict[str, List[Violation]],
        id_violations: List[Violation],
    ) -> List[str]:
        lines = [
            "## 4. 问题汇总",
            "",
        ]

        all_violations: List[Violation] = list(id_violations)
        for viols in violations_by_user.values():
            all_violations.extend(viols)

        if not all_violations:
            lines.append("（无问题）")
        else:
            lines.append("| 用户 | 规则 | 描述 | 详情 |")
            lines.append("|------|------|------|------|")
            for v in all_violations:
                detail = v.detail or ""
                lines.append(f"| {v.user_id} | {v.rule} | {v.description} | {detail} |")

        return lines


# ---------------------------------------------------------------------------
# Test / smoke run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    from rule_engine import RuleEngine
    from tracking_plan import TrackingPlan
    from fixed_account_generator import FixedAccountGenerator
    from event_sequencer import EventSequencer
    from constraint_validator import ConstraintValidator
    from datetime import datetime

    engine = RuleEngine("rules/special/westk/business_logic.yaml")
    plan = TrackingPlan("refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx")
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    sequencer = EventSequencer(engine, plan)
    validator = ConstraintValidator()

    start_ms = int(datetime(2026, 5, 1, 9, 0).timestamp() * 1000)
    events_by_user = {}
    violations_by_user = {}
    for user in users:
        events = sequencer.generate_all_events(user, start_ms)
        events_by_user[user.user_id] = events
        violations_by_user[user.user_id] = validator.validate_all(user, events)

    id_violations = ConstraintValidator.validate_id_mapping(users)

    reporter = ReportGenerator(
        engine,
        "refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx",
        "../mock_data",
    )
    report_path = reporter.generate(users, events_by_user, violations_by_user, id_violations)
    print(f"Report: {report_path}")
    # 打印报告前50行
    with open(report_path) as f:
        for i, line in enumerate(f):
            if i >= 50:
                break
            print(line, end="")
