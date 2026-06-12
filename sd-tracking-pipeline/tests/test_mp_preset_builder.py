"""Tests for mp_preset_builder.py."""
from mp_preset_builder import MpPresetBuilder


def test_generate_scene_returns_string():
    builder = MpPresetBuilder()
    scene = builder.generate_scene()
    assert scene.isdigit()
    assert 1000 <= int(scene) <= 9999


def test_build_launch_props_contains_required_fields():
    builder = MpPresetBuilder()
    props = builder.build_launch_props()
    assert "$scene" in props
    assert "$url" in props
    assert "$utm_source" in props
    assert "$utm_medium" in props


def test_build_hide_props_uses_current_url():
    builder = MpPresetBuilder()
    props = builder.build_hide_props("/pages/index")
    assert props["$url"] == "/pages/index"


def test_build_page_props_with_referrer():
    builder = MpPresetBuilder()
    props = builder.build_page_props("/pages/index", "/pages/home")
    assert props["$url"] == "/pages/index"
    assert props["$referrer"] == "/pages/home"


def test_build_page_leave_props_has_duration():
    builder = MpPresetBuilder()
    props = builder.build_page_leave_props("/pages/index")
    assert "$duration" in props
    assert 5 <= props["$duration"] <= 300


def test_build_click_props():
    builder = MpPresetBuilder()
    props = builder.build_click_props()
    assert "$element_type" in props
    assert "$element_content" in props
    assert "$element_id" in props


def test_build_share_props():
    builder = MpPresetBuilder()
    props = builder.build_share_props()
    assert "$scene" in props
    assert "$share_title" in props
    assert "$share_path" in props


def test_build_props_for_event_dispatch():
    builder = MpPresetBuilder()
    assert "$scene" in builder.build_props_for_event("$MPLaunch")
    assert "$url" in builder.build_props_for_event("$MPHide", current_url="/pages/index")
    assert "$duration" in builder.build_props_for_event("$MPPageLeave")
    assert "$element_type" in builder.build_props_for_event("$MPClick")
    assert "$share_title" in builder.build_props_for_event("$MPShare")
    assert builder.build_props_for_event("UnknownEvent") == {}


def test_custom_page_routes():
    routes = ["/a", "/b"]
    builder = MpPresetBuilder(page_routes=routes)
    props = builder.build_launch_props()
    assert props["$url"] in routes
