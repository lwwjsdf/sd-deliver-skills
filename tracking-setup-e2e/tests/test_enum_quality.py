"""
Tests for list_enum_values.py — enum quality detection logic.

Fixtures are derived from the real Tracking Plan:
  Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx

Run:
    python3 -m pytest tracking-setup-e2e/tests/test_enum_quality.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from list_enum_values import (
    EnumIssue,
    _dedup_issues,
    _is_example_value,
    _is_long_description,
    _is_placeholder,
    analyze_property,
    check_cross_event_consistency,
)


# ── _is_placeholder ────────────────────────────────────────────────────────────

class TestIsPlaceholder:
    @pytest.mark.parametrize("value", [
        "test", "testContent", "testID", "testName", "testType",  # from $MPClick
        "placeholder", "TODO", "TBD", "xxx", "dummy", "foo", "bar",
        "TEST", "TestContent",  # case-insensitive
    ])
    def test_detects_placeholder(self, value):
        assert _is_placeholder(value)

    @pytest.mark.parametrize("value", [
        "M+", "HKPM", "展览", "演出", "微信好友",  # real enum values
        "小程序内购票", "自定义输入", "收藏", "取消收藏",
        "验证码错误", "网络原因",
    ])
    def test_passes_real_values(self, value):
        assert not _is_placeholder(value)


# ── _is_long_description ───────────────────────────────────────────────────────

class TestIsLongDescription:
    def test_detects_purchaseType_blob(self):
        # Real value from Membership_Purchase.purchaseType — description leaked into enum
        blob = (
            '小程序外购票". Members who purchase tickets to upgrade within the mini program '
            'will report "小程序内购票"; members who purchase membership cards directly within '
            'the mini program will report "小程序内购卡"'
        )
        assert _is_long_description(blob)

    @pytest.mark.parametrize("value", [
        "小程序内购票", "小程序内购卡", "小程序外购票",  # the clean values in same field
        "M+", "HKPM", "展览", "演出", "文创套票",
        "香港故宫文化博物馆",  # 9 chars, fine
    ])
    def test_passes_short_values(self, value):
        assert not _is_long_description(value)

    def test_detects_long_english_sentence(self):
        assert _is_long_description(
            "Fixed value: members who purchase tickets to upgrade will report this value"
        )


# ── _is_example_value ──────────────────────────────────────────────────────────

class TestIsExampleValue:
    @pytest.mark.parametrize("value", [
        "1212@qq.com",   # from Form_Operate.inputContent
        "2324",          # pure number ≥4 digits
        "823182",        # pure number ≥4 digits
        "1999-08",       # from Membership_Activation.activateBirthdayList
        "2004-10",
        "+86 138-0000-0001",  # phone
    ])
    def test_detects_example_values(self, value):
        assert _is_example_value(value)

    @pytest.mark.parametrize("value", [
        "M+", "展览", "微信好友", "自定义输入",
        "单人", "双人", "家庭",  # Chinese enum values
        "PA", "WestK",          # short codes
    ])
    def test_passes_real_enum_values(self, value):
        assert not _is_example_value(value)


# ── analyze_property ───────────────────────────────────────────────────────────

class TestAnalyzeProperty:

    # ── Placeholder (严重) ──────────────────────────────────────────────────
    def test_all_placeholders_is_critical(self):
        issues = analyze_property(
            "$element_content", ["test", "testContent"], "$MPClick"
        )
        assert len(issues) == 1
        assert issues[0].severity == "严重"
        assert "纯占位符" in issues[0].description

    def test_mixed_placeholder_is_medium(self):
        issues = analyze_property(
            "someField", ["微信好友", "test"], "SomeEvent"
        )
        assert any(i.severity == "中等" and "占位符" in i.description for i in issues)

    # ── Long description (严重) ─────────────────────────────────────────────
    def test_long_description_in_enum_is_critical(self):
        # purchaseType: one value is a full paragraph
        values = [
            "小程序内购票",
            "小程序内购卡",
            '小程序外购票". Members who purchase tickets to upgrade within the mini program '
            'will report "小程序内购票"; members who purchase membership cards directly '
            'within the mini program will report "小程序内购卡"',
        ]
        issues = analyze_property("purchaseType", values, "Membership_Purchase")
        assert any(i.severity == "严重" and "整段说明文字" in i.description for i in issues)

    # ── ID field with Chinese values (严重) ─────────────────────────────────
    def test_id_field_with_chinese_values_is_critical(self):
        # membershipNumber: type=number, values are membership type names
        issues = analyze_property(
            "membershipNumber", ["单人", "青年", "长者", "双人", "家庭"],
            "Membership_Activation"
        )
        assert any(i.severity == "严重" and "ID/编号" in i.description for i in issues)

    def test_venueID_with_chinese_names_is_critical(self):
        issues = analyze_property(
            "venueID", ["M+", "香港故宫文化博物馆", "自由空间", "艺术公园"],
            "Product_Collection"
        )
        assert any(i.severity == "严重" and "ID/编号" in i.description for i in issues)

    # ── Example values (中等) ───────────────────────────────────────────────
    def test_email_and_numbers_are_medium(self):
        issues = analyze_property(
            "inputContent", ["1212@qq.com", "2324", "823182"], "Form_Operate"
        )
        assert any(i.severity == "中等" and "示例值" in i.description for i in issues)

    def test_date_examples_are_medium(self):
        issues = analyze_property(
            "activateBirthdayList", ["1999-08", "2004-10"], "Membership_Activation"
        )
        assert any(i.severity == "中等" and "示例值" in i.description for i in issues)

    # ── Single value (中等) ─────────────────────────────────────────────────
    def test_single_value_is_medium(self):
        issues = analyze_property("keywordType", ["自定义输入"], "Search_Result")
        assert len(issues) == 1
        assert issues[0].severity == "中等"
        assert "只有" in issues[0].description

    # ── Two values (轻微) ───────────────────────────────────────────────────
    def test_two_values_is_minor(self):
        issues = analyze_property(
            "transferMethod", ["微信好友", "取消"], "Membership_Transfer"
        )
        assert len(issues) == 1
        assert issues[0].severity == "轻微"

    def test_two_values_gender_is_minor(self):
        issues = analyze_property("gender", ["男", "女"], "用户属性")
        assert len(issues) == 1
        assert issues[0].severity == "轻微"

    # ── Clean cases (no issues) ─────────────────────────────────────────────
    def test_clean_businessUnit_no_issues(self):
        issues = analyze_property(
            "businessUnit", ["M+", "HKPM", "PA", "WestK"], "Membership_Activation"
        )
        assert issues == []

    def test_clean_productType_no_issues(self):
        issues = analyze_property(
            "productType", ["展览", "演出", "文创套票", "放映节目"], "Product_Collection"
        )
        assert issues == []

    def test_clean_shareMethod_no_issues(self):
        issues = analyze_property(
            "shareMethod", ["微信好友", "朋友圈", "保存图片", "取消"], "Product_Share"
        )
        assert issues == []


# ── check_cross_event_consistency ─────────────────────────────────────────────

class TestCrossEventConsistency:

    def test_venueID_inconsistency_detected(self):
        # Product_Collection uses ['M+', '香港故宫文化博物馆', '自由空间', '艺术公园']
        # Resource_Position_Click uses ['M+博物馆', '香港故宫文化博物馆', '西九演艺']
        event_sections = {
            "Product_Collection": [
                ("venueID", "string", ["M+", "香港故宫文化博物馆", "自由空间", "艺术公园"], ""),
            ],
            "Resource_Position_Click": [
                ("venueID", "string", ["M+博物馆", "香港故宫文化博物馆", "西九演艺"], ""),
            ],
        }
        issues = check_cross_event_consistency(event_sections)
        assert any(i.field == "venueID" and i.severity == "轻微" for i in issues)

    def test_consistent_field_no_issue(self):
        # Same values in both events → no issue
        event_sections = {
            "EventA": [("productType", "string", ["展览", "演出"], "")],
            "EventB": [("productType", "string", ["展览", "演出"], "")],
        }
        issues = check_cross_event_consistency(event_sections)
        assert issues == []

    def test_single_event_no_issue(self):
        event_sections = {
            "EventA": [("venueID", "string", ["M+", "HKPM"], "")],
        }
        issues = check_cross_event_consistency(event_sections)
        assert issues == []


# ── _dedup_issues ──────────────────────────────────────────────────────────────

class TestDedupIssues:

    def test_same_field_same_description_merged(self):
        issues = [
            EnumIssue("严重", "$element_content", "$MPClick", "纯占位符", "无意义"),
            EnumIssue("严重", "$element_content", "$MPShare", "纯占位符", "无意义"),
        ]
        result = _dedup_issues(issues)
        assert len(result) == 1
        assert "多个来源" in result[0].context

    def test_different_fields_not_merged(self):
        issues = [
            EnumIssue("严重", "$element_content", "$MPClick", "纯占位符", "无意义"),
            EnumIssue("严重", "$element_id", "$MPClick", "纯占位符", "无意义"),
        ]
        result = _dedup_issues(issues)
        assert len(result) == 2

    def test_same_field_different_description_not_merged(self):
        issues = [
            EnumIssue("严重", "venueID", "EventA", "ID/编号格式但值为中文", "语义不符"),
            EnumIssue("轻微", "venueID", "EventA / EventB", "跨事件值域不一致", "不匹配"),
        ]
        result = _dedup_issues(issues)
        assert len(result) == 2
