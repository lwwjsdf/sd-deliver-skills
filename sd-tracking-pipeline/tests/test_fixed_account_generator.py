"""Tests for fixed_account_generator.py."""
from dataclasses import dataclass, field
from typing import Dict, List

import pytest

from fixed_account_generator import (
    _make_identities,
    FixedAccountGenerator,
    BatchUserGenerator,
    User,
)


@dataclass
class FakeAccount:
    id: str
    segment: str
    region: str
    identities: Dict = field(default_factory=dict)
    split_identity: bool = False
    split_groups: List[Dict] = field(default_factory=list)


class FakeRuleEngine:
    def get_fixed_accounts(self):
        return [
            FakeAccount("ACC-1", "L1", "mainland", {"mobile": "13800000001"}),
            FakeAccount("ACC-2", "L2", "hongkong", {"email": "a@b.com"}),
            FakeAccount("ACC-3", "L0", "mainland"),
        ]

    def get_user_segments(self):
        @dataclass
        class Segment:
            name: str
            ratio: float
        return [Segment("L1", 0.5), Segment("L2", 0.5)]

    def get_region_distribution(self):
        return {"mainland": 0.6, "hongkong": 0.4}


def test_make_identities_l0_only_anonymous():
    ids = _make_identities("L0", "mainland", 1)
    assert "unionid" in ids
    assert "cookie_id" in ids
    assert "mobile" not in ids
    assert "email" not in ids


def test_make_identities_mainland_has_mobile():
    ids = _make_identities("L1", "mainland", 2)
    assert ids["mobile"].startswith("+86")
    assert "unionid" in ids
    assert "cookie_id" in ids
    assert "crm_master_id" not in ids


def test_make_identities_non_mainland_has_email():
    ids = _make_identities("L1", "hongkong", 3)
    assert "email" in ids
    assert "mobile" not in ids


def test_make_identities_l2_has_crm_id():
    ids = _make_identities("L2", "mainland", 4)
    assert "crm_master_id" in ids


def test_fixed_account_generator_builds_users():
    gen = FixedAccountGenerator(FakeRuleEngine())
    users = gen.generate_accounts()
    assert len(users) == 3
    assert users[0].account_id == "ACC-1"
    assert users[0].segment == "L1"
    assert users[0].identities["mobile"] == "13800000001"


def test_fixed_account_generator_split_identity():
    engine = FakeRuleEngine()
    engine._fixed = [
        FakeAccount(
            "ACC-SPLIT", "L1", "mainland",
            split_identity=True,
            split_groups=[{"mobile": "13800000001"}, {"mobile": "13800000002"}],
        )
    ]
    engine.get_fixed_accounts = lambda: engine._fixed
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    assert len(users) == 2
    assert users[0].user_id == "ACC-SPLIT-1"
    assert users[1].user_id == "ACC-SPLIT-2"


def test_fixed_account_generator_cookie_ids_list():
    engine = FakeRuleEngine()
    engine._fixed = [
        FakeAccount("ACC-COOKIE", "L1", "mainland", {"cookie_ids": ["c1", "c2"]})
    ]
    engine.get_fixed_accounts = lambda: engine._fixed
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    assert users[0].identities["cookie_id"] == "c1"
    assert "cookie_ids" not in users[0].identities


def test_batch_user_generator_produces_n_users():
    gen = BatchUserGenerator(FakeRuleEngine())
    users = gen.generate(5)
    assert len(users) == 5
    for u in users:
        assert isinstance(u, User)
        assert u.user_id.startswith("user_")
        assert u.segment in ("L1", "L2")
        assert u.region in ("mainland", "hongkong")


def test_batch_user_generator_identities_by_segment():
    gen = BatchUserGenerator(FakeRuleEngine())
    users = gen.generate(10)
    mainland_users = [u for u in users if u.region == "mainland"]
    for u in mainland_users:
        assert "mobile" in u.identities
    hongkong_users = [u for u in users if u.region == "hongkong"]
    for u in hongkong_users:
        assert "email" in u.identities
