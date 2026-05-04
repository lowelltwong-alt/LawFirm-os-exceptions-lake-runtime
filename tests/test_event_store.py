from __future__ import annotations

from pathlib import Path

from exceptions_lake_runtime.event_store import EventStore


def test_appends_multiple_records_without_overwriting(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "runtime_data" / "events.jsonl")

    store.append({"event_id": "EXC-900001", "schema_id": "exception-event-v1"})
    store.append({"event_id": "EXC-900002", "schema_id": "exception-event-v1"})

    assert [record["event_id"] for record in store.list_records()] == [
        "EXC-900001",
        "EXC-900002",
    ]


def test_preserves_payload_and_validation_metadata(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "runtime_data" / "events.jsonl")
    record = {
        "record_type": "synthetic_exception_event",
        "event_id": "EXC-900001",
        "received_at": "2026-04-24T12:00:00Z",
        "contract_version": "abc123",
        "schema_id": "exception-event-v1",
        "validation_result": {"valid": True, "errors": []},
        "policy_result": {"allowed": True, "reason": "synthetic_test_only_allowed"},
        "payload": {"summary": "Synthetic retrieval miss for local testing only."},
    }

    store.append(record)
    stored_record = store.list_records()[0]

    assert stored_record["payload"]["summary"].startswith("Synthetic retrieval miss")
    assert stored_record["validation_result"]["valid"] is True
    assert stored_record["policy_result"]["allowed"] is True


def test_writes_only_under_runtime_data(tmp_path: Path) -> None:
    path = tmp_path / "runtime_data" / "events.jsonl"
    store = EventStore(path)
    store.append({"event_id": "EXC-900001"})

    assert path.exists()
    assert path.parent.name == "runtime_data"
