"""Tests for event_sequencer.py (deterministic parts)."""
import datetime

from event_sequencer import Event, PropertyEnumResolver, EventSequencer, EventSequence, EventDef
from fixed_account_generator import User


def test_event_to_track_record():
    user = User(
        user_id="u1",
        segment="L1",
        region="CN",
        identities={"crm_master_id": "CRM-001", "mobile": "13800000000"},
        profile={},
        created_at=datetime.datetime.now(),
    )
    event = Event(
        event_name="Login",
        user=user,
        timestamp_ms=int(datetime.datetime(2025, 1, 1).timestamp() * 1000),
        properties={"platformType": "MP"},
    )
    record = event.to_track_record("default", [])
    assert record["distinct_id"] == "CRM-001"
    assert record["type"] == "track"
    assert record["event"] == "Login"
    assert record["properties"]["platformType"] == "MP"
    assert record["properties"]["$lib"] == "python"


def test_property_enum_resolver_list():
    resolver = PropertyEnumResolver({"color": ["red", "green", "blue"]})
    assert resolver.resolve("color") in ["red", "green", "blue"]


def test_property_enum_resolver_scalar():
    resolver = PropertyEnumResolver({"app": "MyApp"})
    assert resolver.resolve("app") == "MyApp"


def test_property_enum_resolver_date_range():
    resolver = PropertyEnumResolver({
        "validPeriod": {
            "type": "date_range",
            "date_format": "%Y.%m.%d",
            "format": "{start} - {end}",
            "start_range": ["2025-01-01", "2025-01-02"],
            "duration_days": [1, 1],
        }
    })
    val = resolver.resolve("validPeriod")
    assert " - " in val
    assert "2025." in val


def test_property_enum_resolver_datetime():
    resolver = PropertyEnumResolver({
        "showTime": {
            "type": "datetime",
            "format": "%Y/%m/%d %H:%M:%S",
            "range": ["2025-01-01T00:00:00", "2025-01-01T00:15:00"],
        }
    })
    val = resolver.resolve("showTime")
    assert isinstance(val, str)
    assert "/" in val


def test_weighted_choice():
    seq_a = EventSequence(name="a", events=[], conversion_rate=0.8)
    seq_b = EventSequence(name="b", events=[], conversion_rate=0.2)
    chosen = EventSequencer._weighted_choice([seq_a, seq_b])
    assert chosen in (seq_a, seq_b)


def test_weighted_choice_empty():
    assert EventSequencer._weighted_choice([]) is None


def test_property_enum_resolver_date_relative_to_today():
    resolver = PropertyEnumResolver({
        "expirationTime": {
            "type": "date_relative_to_today",
            "distribution": {"expired": 1.0},
            "expired_range": [-10, -1],
            "active_range": [1, 10],
        }
    })
    val = resolver.resolve("expirationTime")
    result = datetime.datetime.strptime(val, "%Y-%m-%d").date()
    assert (datetime.date.today() - result).days >= 1


def test_property_enum_resolver_weighted_int():
    resolver = PropertyEnumResolver({
        "ticketsQuantity": {
            "type": "weighted_int",
            "values": [
                {"value": 1, "weight": 0},
                {"value": 2, "weight": 1},
            ],
        }
    })
    assert resolver.resolve("ticketsQuantity") == 2


def test_property_enum_resolver_range():
    resolver = PropertyEnumResolver({
        "paidAmount": {"type": "range", "min": 100, "max": 200}
    })
    val = resolver.resolve("paidAmount")
    assert 100 <= val <= 200
