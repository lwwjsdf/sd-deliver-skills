from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class User:
    user_id: str                     # 内部标识，固定账号用 account.id（如 UAT-X01）
    segment: str                     # L0-L4
    region: str                      # mainland / hongkong / overseas
    identities: Dict[str, str]       # {crm_master_id: ..., email: ..., mobile: ..., unionid: ..., cookie_id: ...}
                                     # 只包含该账号实际有的 ID，None 值不包含
    profile: Dict[str, Any]          # 用户属性（初始为空，由 EventSequencer 填充）
    created_at: datetime
    account_id: Optional[str] = None # 原始 fixed_account id（如 UAT-X01），split 时保留


class FixedAccountGenerator:
    def __init__(self, rule_engine):
        self.rule_engine = rule_engine

    def generate_accounts(self) -> List[User]:
        """
        生成所有固定测试账号。
        - split_identity=False：每个 FixedAccount 生成1个 User
        - split_identity=True：按 split_groups 生成多个 User，每组独立 user_id
          UAT-X07 示例：split_groups=[{mobile:..., unionid:...}, {email:..., cookie_id:...}]
          → 生成2个 User，user_id 分别为 UAT-X07-1, UAT-X07-2
        """
        users = []
        for account in self.rule_engine.get_fixed_accounts():
            if account.split_identity and account.split_groups:
                for i, group in enumerate(account.split_groups, start=1):
                    suffix = f"-{i}"
                    user = self._build_user(account, group, suffix=suffix)
                    users.append(user)
            else:
                # Build identities from account.identities, handling cookie_ids specially
                identities = dict(account.identities)
                # cookie_ids list → use first as cookie_id, drop the rest
                if "cookie_ids" in identities:
                    cookie_ids = identities.pop("cookie_ids")
                    if isinstance(cookie_ids, list) and cookie_ids:
                        identities["cookie_id"] = cookie_ids[0]
                user = self._build_user(account, identities)
                users.append(user)
        return users

    def _build_user(self, account, identities: Dict, suffix: str = "") -> "User":
        """
        从 FixedAccount 构建 User。
        - user_id = account.id + suffix（suffix 为空时直接用 account.id）
        - identities 只包含非 None 值
        - created_at = datetime.now()
        """
        user_id = account.id + suffix
        # Filter out None values
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
