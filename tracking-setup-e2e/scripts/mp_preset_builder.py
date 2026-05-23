"""
mp_preset_builder.py — Generate realistic properties for WeChat Mini Program preset events.

Handles $MPLaunch, $MPShow, $MPHide, $MPPageLeave, $MPPageShow, $MPClick, $MPShare.
Scene values and UTM mapping are built-in; page_routes and utm_campaigns are
optionally overridden via business_logic.yaml preset_events config.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Scene value groups with empirical weights
# Source: https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html
# ---------------------------------------------------------------------------

_SCENE_GROUPS: List[Tuple[float, List[int]]] = [
    (0.25, [1001, 1089, 1103, 1104, 1271]),  # 下拉/最近使用
    (
        0.20,
        [1007, 1008, 1044, 1073, 1074, 1096, 1185, 1202, 1207, 1208],
    ),  # 分享/消息卡片
    (0.18, [1005, 1006, 1027, 1053, 1106, 1183, 1232, 1245, 1252, 1297]),  # 搜索
    (0.12, [1011, 1012, 1013, 1047, 1048, 1049, 1025, 1031, 1032, 1150]),  # 扫码
    (0.10, [1035, 1043, 1058, 1067, 1091, 1157, 1158, 1184, 1261, 1305]),  # 公众号/文章
    (0.08, [1037, 1038, 1135, 1168, 1169]),  # 小程序互跳
    (0.04, [1019, 1028, 1029, 1034, 1057, 1071, 1072, 1097]),  # 支付/卡包
    (
        0.03,
        [
            1000,
            1010,
            1014,
            1017,
            1023,
            1024,
            1030,
            1036,
            1039,  # 其他
            1042,
            1045,
            1046,
            1052,
            1054,
            1056,
            1059,
            1060,
            1064,
            1065,
            1068,
            1069,
            1077,
            1078,
            1079,
            1081,
            1082,
            1084,
            1088,
            1090,
            1092,
            1095,
            1099,
            1100,
            1101,
            1102,
            1107,
        ],
    ),
]

# scene_id → (utm_source, utm_medium)
_UTM_MAP: Dict[int, Tuple[str, str]] = {}


def _build_utm_map():
    search_scenes = {1005, 1006, 1027, 1053, 1106, 1183, 1232, 1245, 1252, 1297}
    share_scenes = {1007, 1008, 1044, 1073, 1074, 1096, 1185, 1202, 1207, 1208}
    qrcode_scenes = {1011, 1012, 1013, 1047, 1048, 1049, 1025, 1031, 1032, 1150}
    oa_scenes = {1035, 1043, 1058, 1067, 1091, 1157, 1158, 1184, 1261, 1305}
    mp_jump_scenes = {1037, 1038, 1135, 1168, 1169}
    pay_scenes = {1019, 1028, 1029, 1034, 1057, 1071, 1072, 1097}
    recent_scenes = {1001, 1089, 1103, 1104, 1271}

    for sid in search_scenes:
        _UTM_MAP[sid] = ("wechat_search", "mini_program_search")
    for sid in share_scenes:
        _UTM_MAP[sid] = ("wechat_share", "mini_program_card")
    for sid in qrcode_scenes:
        _UTM_MAP[sid] = ("qrcode", "scan")
    for sid in oa_scenes:
        _UTM_MAP[sid] = ("official_account", "mp_menu")
    for sid in mp_jump_scenes:
        _UTM_MAP[sid] = ("mini_program", "mp_jump")
    for sid in pay_scenes:
        _UTM_MAP[sid] = ("wechat_pay", "pay_result")
    for sid in recent_scenes:
        _UTM_MAP[sid] = ("direct", "recent_used")


_build_utm_map()

_DEFAULT_PAGE_ROUTES = [
    "/pages/index/index",
    "/pages/event/list",
    "/pages/event/detail",
    "/pages/ticket/buy",
    "/pages/member/center",
    "/pages/search/result",
]

_DEFAULT_UTM_CAMPAIGNS = [
    "",  # most sessions have no campaign
    "",
    "",
    "spring_festival_2026",
    "member_day",
    "new_user_gift",
]


class MpPresetBuilder:
    def __init__(
        self,
        page_routes: Optional[List[str]] = None,
        utm_campaigns: Optional[List[str]] = None,
        scene_weights: Optional[Dict[str, float]] = None,
    ):
        self._page_routes = page_routes or _DEFAULT_PAGE_ROUTES
        self._utm_campaigns = utm_campaigns or _DEFAULT_UTM_CAMPAIGNS

        # Build flat weighted scene list
        groups = _SCENE_GROUPS
        if scene_weights:
            # scene_weights keys are group names; rebuild weights by position
            group_names = [
                "下拉/最近使用",
                "分享/消息卡片",
                "搜索",
                "扫码",
                "公众号/文章",
                "小程序互跳",
                "支付/卡包",
                "其他",
            ]
            groups = [
                (scene_weights.get(group_names[i], w), scenes)
                for i, (w, scenes) in enumerate(_SCENE_GROUPS)
            ]

        self._scene_pool: List[int] = []
        self._scene_weights: List[float] = []
        for weight, scenes in groups:
            per_scene = weight / len(scenes)
            for sid in scenes:
                self._scene_pool.append(sid)
                self._scene_weights.append(per_scene)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_scene(self) -> str:
        """Return a scene value as string (matches SA SDK format)."""
        sid = random.choices(self._scene_pool, weights=self._scene_weights, k=1)[0]
        return str(sid)

    def build_launch_props(self) -> Dict[str, Any]:
        """Properties for $MPLaunch and $MPShow."""
        scene_str = self.generate_scene()
        scene_id = int(scene_str)
        utm_source, utm_medium = _UTM_MAP.get(scene_id, ("direct", "unknown"))
        campaign = random.choice(self._utm_campaigns)

        props: Dict[str, Any] = {
            "$scene": scene_str,
            "$url": random.choice(self._page_routes),
            "$utm_source": utm_source,
            "$utm_medium": utm_medium,
        }
        if campaign:
            props["$utm_campaign"] = campaign
        return props

    def build_hide_props(self, current_url: str = "") -> Dict[str, Any]:
        """Properties for $MPHide."""
        props: Dict[str, Any] = {}
        # $MPHide 不生成场景值，保持空
        if current_url:
            props["$url"] = current_url
        return props

    def build_page_props(
        self, current_url: str = "", referrer: str = ""
    ) -> Dict[str, Any]:
        """Properties for $MPPageShow and $MPPageLeave."""
        if not current_url:
            current_url = random.choice(self._page_routes)
        props: Dict[str, Any] = {"$url": current_url}
        if referrer:
            props["$referrer"] = referrer
        return props

    def build_page_leave_props(
        self, current_url: str = "", referrer: str = ""
    ) -> Dict[str, Any]:
        """Properties for $MPPageLeave — adds $duration."""
        props = self.build_page_props(current_url, referrer)
        props["$duration"] = random.randint(5, 300)
        return props

    def build_click_props(self) -> Dict[str, Any]:
        """Properties for $MPClick."""
        element_types = ["button", "link", "image", "tab"]
        element_contents = [
            "立即购买",
            "查看详情",
            "加入收藏",
            "立即预订",
            "了解更多",
            "返回首页",
            "搜索",
            "确认",
        ]
        etype = random.choice(element_types)
        return {
            "$element_type": etype,
            "$element_content": random.choice(element_contents),
            "$element_id": f"{etype}_{random.randint(1, 99):02d}",
            "$url": random.choice(self._page_routes),
        }

    def build_share_props(self) -> Dict[str, Any]:
        """Properties for $MPShare."""
        scene_str = self.generate_scene()
        share_titles = [
            "快来参加这个活动！",
            "好活动分享给你",
            "限时优惠，不要错过",
            "我在这里等你",
            "一起来体验吧",
        ]
        path = random.choice(self._page_routes)
        return {
            "$scene": scene_str,
            "$url": path,
            "$share_title": random.choice(share_titles),
            "$share_path": path,
        }

    def build_props_for_event(
        self, event_name: str, current_url: str = "", referrer: str = ""
    ) -> Dict[str, Any]:
        """Dispatch to the right builder based on event name."""
        if event_name in ("$MPLaunch", "$MPShow"):
            return self.build_launch_props()
        if event_name == "$MPHide":
            return self.build_hide_props(current_url)
        if event_name == "$MPPageShow":
            return self.build_page_props(current_url, referrer)
        if event_name == "$MPPageLeave":
            return self.build_page_leave_props(current_url, referrer)
        if event_name == "$MPClick":
            return self.build_click_props()
        if event_name == "$MPShare":
            return self.build_share_props()
        return {}


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    builder = MpPresetBuilder()

    print("=== $MPLaunch ===")
    for _ in range(5):
        print(builder.build_launch_props())

    print("\n=== scene distribution (n=1000) ===")
    from collections import Counter

    scenes = [builder.generate_scene() for _ in range(1000)]
    # group by first digit of scene id
    groups = Counter()
    for s in scenes:
        sid = int(s)
        if sid in {1001, 1089, 1103, 1104, 1271}:
            groups["下拉/最近使用"] += 1
        elif sid in {1007, 1008, 1044, 1073, 1074, 1096, 1185, 1202, 1207, 1208}:
            groups["分享/消息卡片"] += 1
        elif sid in {1005, 1006, 1027, 1053, 1106, 1183, 1232, 1245, 1252, 1297}:
            groups["搜索"] += 1
        else:
            groups["其他"] += 1
    for g, n in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {g}: {n / 10:.1f}%")
