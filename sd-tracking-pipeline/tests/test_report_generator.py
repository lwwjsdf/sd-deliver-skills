"""Tests for report_generator.py."""
import os
from datetime import datetime

from report_generator import ReportGenerator


class FakeRuleEngine:
    def get_meta(self):
        return {"project": "demo"}


def test_generate_report(tmp_path):
    class FakeEvent:
        def __init__(self, name, ts, is_success=True):
            self.event_name = name
            self.timestamp_ms = ts
            self.is_success = is_success

    class FakeUser:
        def __init__(self, uid, account_id=None):
            self.user_id = uid
            self.account_id = account_id
            self.identities = {"mobile": "13800000000"}
            self.profile = {}

    class FakeViolation:
        def __init__(self, user_id, rule, description, detail=""):
            self.user_id = user_id
            self.rule = rule
            self.description = description
            self.detail = detail

    rule_engine = FakeRuleEngine()
    generator = ReportGenerator(rule_engine, "plan.xlsx", str(tmp_path))

    user = FakeUser("u1")
    event = FakeEvent("Login", int(datetime(2025, 1, 1).timestamp() * 1000))
    violation = FakeViolation("u1", "temporal_order", "Registration 在 Login 前")

    path = generator.generate(
        users=[user],
        events_by_user={"u1": [event]},
        violations_by_user={"u1": [violation]},
        id_violations=[],
    )

    assert os.path.exists(path)
    content = open(path, "r", encoding="utf-8").read()
    assert "UAT 测试数据集验证报告" in content
    assert "u1" in content
    assert "Login" in content
    assert "Registration 在 Login 前" in content


def test_generate_report_no_violations(tmp_path):
    class FakeEvent:
        def __init__(self):
            self.event_name = "Login"
            self.timestamp_ms = 0
            self.is_success = True

    class FakeUser:
        def __init__(self):
            self.user_id = "u2"
            self.account_id = None
            self.identities = {}
            self.profile = {}

    generator = ReportGenerator(FakeRuleEngine(), "plan.xlsx", str(tmp_path))
    user = FakeUser()
    path = generator.generate(
        users=[user],
        events_by_user={"u2": [FakeEvent()]},
        violations_by_user={"u2": []},
        id_violations=[],
    )
    content = open(path, "r", encoding="utf-8").read()
    assert "✅ 无违规" in content
    assert "（无问题）" in content


def test_split_account_rendering(tmp_path):
    class FakeUser:
        def __init__(self, uid):
            self.user_id = uid
            self.account_id = "acc1"
            self.identities = {}
            self.profile = {}

    generator = ReportGenerator(FakeRuleEngine(), "plan.xlsx", str(tmp_path))
    users = [FakeUser("u3a"), FakeUser("u3b")]
    path = generator.generate(
        users=users,
        events_by_user={"u3a": [], "u3b": []},
        violations_by_user={"u3a": [], "u3b": []},
        id_violations=[],
    )
    content = open(path, "r", encoding="utf-8").read()
    assert "识别为 2 个独立用户" in content
    assert "✅ 两个用户无共享 identity" in content
