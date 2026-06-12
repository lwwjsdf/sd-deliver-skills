"""Tests for yaml_validator.py."""
import pytest
import yaml

from yaml_validator import YamlValidator, ValidationResult


def _write_yaml(tmp_path, data):
    p = tmp_path / "business_logic.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(p)


def _valid_data():
    return {
        "meta": {"project": "demo", "version": "1.0"},
        "region_distribution": {"mainland": 0.7, "hongkong": 0.3},
        "user_segments": {
            "L1": {"ratio": 0.5},
            "L2": {"ratio": 0.5},
        },
        "identity_priority": {
            "login_id": {"priority": 1, "sa_key": "$login_id"},
        },
        "event_sequences": [{"name": "main", "events": [{"event": "A"}]}],
        "fixed_accounts": [],
    }


def test_valid_yaml_passes(tmp_path):
    path = _write_yaml(tmp_path, _valid_data())
    validator = YamlValidator(path)
    result = validator.validate()
    assert result.passed
    assert len(result.warnings) == 1  # no tracking plan warning


def test_missing_meta_is_error(tmp_path):
    data = _valid_data()
    del data["meta"]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("meta" in i.path and i.level == "error" for i in result.issues)


def test_missing_project_in_meta_is_error(tmp_path):
    data = _valid_data()
    data["meta"] = {"version": "1.0"}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any(i.path == "meta.project" for i in result.issues)


def test_region_distribution_must_sum_to_one(tmp_path):
    data = _valid_data()
    data["region_distribution"] = {"mainland": 0.5, "hongkong": 0.3}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("sum" in i.message for i in result.issues)


def test_unknown_region_is_warning(tmp_path):
    data = _valid_data()
    data["region_distribution"] = {"mainland": 1.0, "mars": 0.0}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert any("mars" in i.message and i.level == "warning" for i in result.issues)


def test_user_segments_must_sum_to_one(tmp_path):
    data = _valid_data()
    data["user_segments"] = {"L1": {"ratio": 0.3}, "L2": {"ratio": 0.5}}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("sum" in i.message for i in result.issues)


def test_negative_segment_ratio_is_error(tmp_path):
    data = _valid_data()
    data["user_segments"] = {"L1": {"ratio": -0.1}, "L2": {"ratio": 1.1}}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert any("non-negative" in i.message for i in result.issues)


def test_identity_priority_list_format_accepted(tmp_path):
    data = _valid_data()
    data["identity_priority"] = {"login_id": ["first", "second"]}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert result.passed


def test_identity_priority_empty_list_is_error(tmp_path):
    data = _valid_data()
    data["identity_priority"] = {"login_id": []}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("Empty list" in i.message for i in result.issues)


def test_identity_priority_dict_requires_fields(tmp_path):
    data = _valid_data()
    data["identity_priority"] = {"login_id": {}}
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("priority" in i.path for i in result.issues)
    assert any("sa_key" in i.path for i in result.issues)


def test_event_sequence_duplicate_name_is_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "events": []},
        {"name": "seq1", "events": []},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("Duplicate" in i.message for i in result.issues)


def test_invalid_condition_syntax_is_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "condition": "invalid syntax", "events": []},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("Unrecognised condition" in i.message for i in result.issues)


@pytest.mark.parametrize("cond", ["segment in [L1,L2]", "has EventA", "not EventB"])
def test_valid_condition_syntax_passes(tmp_path, cond):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "condition": cond, "events": []},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not any("condition" in i.path for i in result.errors)


def test_conversion_rate_out_of_range_is_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "conversion_rate": 1.5, "events": []},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("conversion_rate" in i.path for i in result.issues)


def test_time_after_prev_min_greater_than_max_is_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {
            "name": "seq1",
            "events": [
                {"event": "A", "time_after_prev": {"min": 10, "max": 5}},
            ],
        },
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("min" in i.message and "max" in i.message for i in result.issues)


@pytest.mark.parametrize("repeat", ["5", "{OrderPaid.order_id}"])
def test_valid_repeat_passes(tmp_path, repeat):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "events": [{"event": "A", "repeat": repeat}]},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not any("repeat" in i.path for i in result.errors)


def test_invalid_repeat_is_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "events": [{"event": "A", "repeat": "abc"}]},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("repeat" in i.path for i in result.issues)


def test_fixed_account_duplicate_id_is_error(tmp_path):
    data = _valid_data()
    data["fixed_accounts"] = [
        {"id": "acc1", "segment": "L1"},
        {"id": "acc1", "segment": "L2"},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("Duplicate" in i.message for i in result.issues)


def test_split_identity_requires_split_groups(tmp_path):
    data = _valid_data()
    data["fixed_accounts"] = [
        {"id": "acc1", "segment": "L1", "split_identity": True},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path).validate()
    assert not result.passed
    assert any("split_groups" in i.path for i in result.issues)


class FakeTrackingPlan:
    def list_events(self):
        return ["OrderPaid"]

    def get_event_schema(self, event_name):
        if event_name == "OrderPaid":
            class Schema:
                properties = [type("P", (), {"name": "order_id"})()]
            return Schema()
        return None


def test_unknown_event_with_plan_is_reference_error(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "events": [{"event": "UnknownEvent"}]},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path, tracking_plan=FakeTrackingPlan()).validate()
    assert not result.passed
    assert any(i.layer == "reference" for i in result.issues)


def test_unknown_property_with_plan_is_reference_warning(tmp_path):
    data = _valid_data()
    data["event_sequences"] = [
        {"name": "seq1", "events": [{"event": "OrderPaid", "fields": {"unknown_prop": "x"}}]},
    ]
    path = _write_yaml(tmp_path, data)
    result = YamlValidator(path, tracking_plan=FakeTrackingPlan()).validate()
    assert any(i.layer == "reference" and i.level == "warning" for i in result.issues)
