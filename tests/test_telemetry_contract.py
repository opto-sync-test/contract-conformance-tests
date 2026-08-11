from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from deep_tests.telemetry_contract import TelemetryContractError, validate_record


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "opto-sync-telemetry" / "v1"
VALID = CONTRACT / "fixtures" / "valid"
INVALID = CONTRACT / "fixtures" / "invalid"
EXPECTED_COMMIT = "dddb3bf77ceb894cde538c211bc39a41b4cc6014"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class TelemetryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load(VALID / "state-backoff.json")
        self.completed = load(VALID / "cycle-completed.json")
        self.failed = load(VALID / "cycle-failed.json")

    def test_provenance_pins_every_vendored_byte(self) -> None:
        provenance = load(CONTRACT / "provenance.json")
        self.assertEqual(provenance["manifest_version"], 1)
        self.assertEqual(provenance["contract"], "opto-sync.telemetry/v1")
        self.assertEqual(provenance["product_version"], "0.3.0")
        self.assertEqual(provenance["source"]["repository"], "opto-sync/opto-sync-clients")
        self.assertEqual(provenance["source"]["commit"], EXPECTED_COMMIT)

        entries = provenance["files"]
        listed = {entry["vendored_path"] for entry in entries}
        actual = {
            path.relative_to(CONTRACT).as_posix()
            for path in CONTRACT.rglob("*.json")
            if path.name != "provenance.json"
        }
        self.assertEqual(listed, actual)
        for entry in entries:
            path = CONTRACT / entry["vendored_path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], entry["vendored_path"])
            self.assertEqual(
                entry["source_path"],
                (
                    "schema/opto-sync-telemetry.schema.json"
                    if entry["classification"] == "schema"
                    else f"schema/telemetry-fixtures/{entry['vendored_path'].removeprefix('fixtures/')}"
                ),
            )

    def test_vendored_schema_preserves_the_closed_privacy_boundary(self) -> None:
        schema = load(CONTRACT / "schema.json")
        self.assertFalse(schema["additionalProperties"])
        attributes = schema["$defs"]["attributes"]
        self.assertFalse(attributes["additionalProperties"])
        self.assertEqual(attributes["properties"]["opto.sync.schema"]["const"], "opto-sync.telemetry/v1")
        self.assertNotIn("error.message", attributes["properties"])
        self.assertNotIn("record", schema["properties"])
        self.assertNotIn("payload", schema["properties"])

    def test_all_vendored_valid_fixtures_conform(self) -> None:
        paths = sorted(VALID.glob("*.json"))
        self.assertEqual([path.name for path in paths], [
            "cycle-completed.json",
            "cycle-failed.json",
            "state-backoff.json",
        ])
        for path in paths:
            with self.subTest(path=path.name):
                validate_record(load(path))

    def test_all_vendored_invalid_fixtures_fail_for_the_expected_reason(self) -> None:
        expected = {
            "impossible-calendar-date.json": "real calendar",
            "missing-cycle-counts.json": "missing fields",
            "raw-error-message.json": "privacy-forbidden",
            "raw-record-payload.json": "privacy-forbidden",
            "request-id-too-short.json": "request.id",
            "request-id-with-slash.json": "request.id",
            "state-severity-mismatch.json": "severity",
            "unknown-runtime.json": "runtime",
        }
        self.assertEqual({path.name for path in INVALID.glob("*.json")}, set(expected))
        for name, reason in expected.items():
            with self.subTest(path=name):
                with self.assertRaisesRegex(TelemetryContractError, reason):
                    validate_record(load(INVALID / name))

    def test_request_ids_are_bounded_and_use_only_safe_characters(self) -> None:
        for request_id in ("abcdEF12", "a" * 128, "sync:cycle_42.v1"):
            with self.subTest(valid=request_id):
                record = copy.deepcopy(self.state)
                record["attributes"]["request.id"] = request_id
                validate_record(record)
        for request_id in ("a" * 7, "a" * 129, "has/slash", "contains space", "ünicode123"):
            with self.subTest(invalid=request_id):
                record = copy.deepcopy(self.state)
                record["attributes"]["request.id"] = request_id
                with self.assertRaisesRegex(TelemetryContractError, "request.id"):
                    validate_record(record)

    def test_timestamps_must_name_real_calendar_milliseconds_in_utc(self) -> None:
        for timestamp in ("2024-02-29T23:59:59.999Z", "2026-01-01T00:00:00.000Z"):
            with self.subTest(valid=timestamp):
                record = copy.deepcopy(self.state)
                record["timestamp"] = timestamp
                validate_record(record)
        for timestamp in (
            "2023-02-29T23:59:59.999Z",
            "2026-04-31T00:00:00.000Z",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00.000+00:00",
        ):
            with self.subTest(invalid=timestamp):
                record = copy.deepcopy(self.state)
                record["timestamp"] = timestamp
                with self.assertRaises(TelemetryContractError):
                    validate_record(record)

    def test_event_kind_status_and_severity_are_consistent(self) -> None:
        expected = {
            "stopped": ("INFO", 9),
            "idle": ("INFO", 9),
            "syncing": ("INFO", 9),
            "offline": ("WARN", 13),
            "backoff": ("WARN", 13),
            "error": ("ERROR", 17),
        }
        for status, severity in expected.items():
            with self.subTest(status=status):
                record = copy.deepcopy(self.state)
                record["attributes"]["opto.sync.status"] = status
                record["severityText"], record["severityNumber"] = severity
                validate_record(record)
                record["severityText"], record["severityNumber"] = "ERROR", 17
                if severity != ("ERROR", 17):
                    with self.assertRaisesRegex(TelemetryContractError, "severity"):
                        validate_record(record)

        wrong_body = copy.deepcopy(self.completed)
        wrong_body["body"] = "opto-sync state changed"
        with self.assertRaisesRegex(TelemetryContractError, "completed cycle"):
            validate_record(wrong_body)

    def test_cycle_and_error_fields_are_required_and_bounded(self) -> None:
        required = (
            "opto.sync.pushed_mutations",
            "opto.sync.acknowledged_mutations",
            "opto.sync.pulled_changes",
            "opto.sync.installed_snapshots",
            "opto.sync.has_more_pending",
        )
        for field in required:
            with self.subTest(missing=field):
                record = copy.deepcopy(self.completed)
                del record["attributes"][field]
                with self.assertRaisesRegex(TelemetryContractError, "missing fields"):
                    validate_record(record)

        for field, value in (
            ("opto.sync.pushed_mutations", -1),
            ("opto.sync.pulled_changes", True),
            ("opto.sync.has_more_pending", 1),
        ):
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.completed)
                record["attributes"][field] = value
                with self.assertRaises(TelemetryContractError):
                    validate_record(record)

        missing_error = copy.deepcopy(self.failed)
        del missing_error["attributes"]["error.code"]
        with self.assertRaisesRegex(TelemetryContractError, "requires error.code"):
            validate_record(missing_error)
        for error_code in ("lowercase", "1LEADING_DIGIT", "A" * 129):
            with self.subTest(error_code=error_code):
                record = copy.deepcopy(self.failed)
                record["attributes"]["error.code"] = error_code
                with self.assertRaisesRegex(TelemetryContractError, "error.code"):
                    validate_record(record)

    def test_privacy_forbidden_payload_fields_fail_closed_at_any_depth(self) -> None:
        for field in (
            "payload",
            "record",
            "checkpoint",
            "mutation",
            "error.message",
            "exception.stacktrace",
            "http.request.body",
            "db.statement",
        ):
            with self.subTest(field=field):
                record = copy.deepcopy(self.state)
                record["attributes"][field] = "sensitive value"
                with self.assertRaisesRegex(TelemetryContractError, "privacy-forbidden"):
                    validate_record(record)


if __name__ == "__main__":
    unittest.main()
