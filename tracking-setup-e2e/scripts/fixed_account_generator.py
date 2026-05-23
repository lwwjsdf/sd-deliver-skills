from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import random
import string


@dataclass
class User:
    user_id: str
    segment: str
    region: str
    identities: Dict[str, str]
    profile: Dict[str, Any]
    created_at: datetime
    account_id: Optional[str] = None


def _rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _make_identities(segment: str, region: str, idx: int) -> Dict[str, str]:
    """根据 segment 和 region 生成合理的 identity 集合。"""
    ids: Dict[str, str] = {}

    # L0: 只有匿名 ID
    if segment == "L0":
        ids["unionid"] = f"wxu_{idx:06d}"
        ids["cookie_id"] = f"ck_{idx:06d}"
        return ids

    # L1+: 有注册，根据地区决定 mobile 还是 email
    if region == "mainland":
        ids["mobile"] = f"+86 138{idx:08d}"[:16]
    else:
        ids["email"] = f"user_{idx:06d}@test.example.com"

    ids["unionid"] = f"wxu_{idx:06d}"
    ids["cookie_id"] = f"ck_{idx:06d}"

    # L2+: 有 CRM ID
    if segment in ("L2", "L3", "L4"):
        ids["crm_master_id"] = f"CRM-{idx:08d}"

    return ids


class FixedAccountGenerator:
    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def generate_accounts(self) -> List[User]:
        users = []
        for account in self.rule_engine.get_fixed_accounts():
            if account.split_identity and account.split_groups:
                for i, group in enumerate(account.split_groups, start=1):
                    user = self._build_user(account, group, suffix=f"-{i}")
                    users.append(user)
            else:
                identities = dict(account.identities)
                if "cookie_ids" in identities:
                    cookie_ids = identities.pop("cookie_ids")
                    if isinstance(cookie_ids, list) and cookie_ids:
                        identities["cookie_id"] = cookie_ids[0]
                user = self._build_user(account, identities)
                users.append(user)
        return users

    def _build_user(self, account, identities: Dict, suffix: str = "") -> User:
        user_id = account.id + suffix
        clean_identities = {k: v for k, v in identities.items() if v is not None}
        return User(
            user_id=user_id,
            segment=account.segment,
            region=account.region,
            identities=clean_identities,
            profile={},
            created_at=datetime.now(),
            account_id=account.id,
        )


class BatchUserGenerator:
    """按 segment/region 比例随机生成 N 个用户。"""

    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def generate(self, n: int) -> List[User]:
        segments = self.rule_engine.get_user_segments()
        region_dist = self.rule_engine.get_region_distribution()

        seg_names = [s.name for s in segments]
        seg_weights = [s.ratio for s in segments]
        region_names = list(region_dist.keys())
        region_weights = list(region_dist.values())

        users = []
        for i in range(1, n + 1):
            segment = random.choices(seg_names, weights=seg_weights, k=1)[0]
            region = random.choices(region_names, weights=region_weights, k=1)[0]
            identities = _make_identities(segment, region, i)
            users.append(User(
                user_id=f"user_{i:06d}",
                segment=segment,
                region=region,
                identities=identities,
                profile={},
                created_at=datetime.now(),
            ))
        return users


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from rule_engine import RuleEngine
    engine = RuleEngine("rules/special/westk/business_logic.yaml")
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    print(f"Generated {len(users)} users:")
    for u in users:
        print(f"  {u.user_id}: segment={u.segment}, region={u.region}, ids={list(u.identities.keys())}")
    # UAT-X07 应生成2个用户
    x07_users = [u for u in users if u.account_id == "UAT-X07"]
    assert len(x07_users) == 2, f"Expected 2 users for UAT-X07, got {len(x07_users)}"
    print("Assertions passed.")
