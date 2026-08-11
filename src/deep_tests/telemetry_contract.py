from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class TelemetryContractError(ValueError):
    """Raised when a record violates the vendored telemetry contract."""


TOP_LEVEL_KEYS = frozenset(
    {
        "body",
        "severityText",
        "severityNumber",
        "timestamp",
        "attributes",
        "traceId",
        "spanId",
        "traceFlags",
        "traceState",
    }
)
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {"body", "severityText", "severityNumber", "timestamp", "attributes"}
)
ATTRIBUTE_KEYS = frozenset(
    {
        "service.name",
        "event.name",
        "opto.sync.schema",
        "opto.sync.runtime",
        "opto.sync.status",
        "opto.sync.consecutive_failures",
        "opto.sync.next_retry_at",
        "opto.sync.pushed_mutations",
        "opto.sync.acknowledged_mutations",
        "opto.sync.pulled_changes",
        "opto.sync.installed_snapshots",
        "opto.sync.has_more_pending",
        "error.code",
        "request.id",
    }
)
REQUIRED_ATTRIBUTE_KEYS = frozenset(
    {
        "service.name",
        "event.name",
        "opto.sync.schema",
        "opto.sync.runtime",
        "opto.sync.status",
        "opto.sync.consecutive_failures",
    }
)
PRIVACY_FORBIDDEN_KEYS = frozenset(
    {
        "payload",
        "record",
        "records",
        "checkpoint",
        "checkpoints",
        "mutation",
        "mutations",
        "error.message",
        "exception.message",
        "exception.stacktrace",
        "http.request.body",
        "http.response.body",
        "db.statement",
    }
)
RUNTIMES = frozenset({"typescript", "dart", "rust"})
STATUSES = frozenset({"stopped", "idle", "syncing", "offline", "backoff", "error"})
EVENTS = frozenset(
    {"opto.sync.state.changed", "opto.sync.cycle.completed", "opto.sync.cycle.failed"}
)
SEVERITY_NUMBERS = {"INFO": 9, "WARN": 13, "ERROR": 17}
STATE_SEVERITIES = {
    "stopped": ("INFO", 9),
    "idle": ("INFO", 9),
    "syncing": ("INFO", 9),
    "offline": ("WARN", 13),
    "backoff": ("WARN", 13),
    "error": ("ERROR", 17),
}
TIMESTAMP = re.compile(
    r"^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{3}Z$"
)
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,127}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
CYCLE_COUNTS = (
    "opto.sync.pushed_mutations",
    "opto.sync.acknowledged_mutations",
    "opto.sync.pulled_changes",
    "opto.sync.installed_snapshots",
)


def _violation(message: str) -> None:
    raise TelemetryContractError(message)


def _require_exact_int(value: Any, field: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        _violation(f"{field} must be an integer in [{minimum}, {maximum}]")


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        _violation(f"{field} must be a canonical millisecond RFC 3339 UTC timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise TelemetryContractError(f"{field} is not a real calendar timestamp") from exc


def _find_forbidden(value: Any, path: str = "record") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PRIVACY_FORBIDDEN_KEYS:
                _violation(f"privacy-forbidden field {key!r} at {path}")
            _find_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _find_forbidden(child, f"{path}[{index}]")


def validate_record(record: Any) -> None:
    """Validate the dependency-free subset mirrored by the vendored JSON Schema."""

    if not isinstance(record, dict):
        _violation("telemetry record must be an object")
    _find_forbidden(record)

    unexpected = set(record) - TOP_LEVEL_KEYS
    if unexpected:
        _violation(f"unexpected top-level fields: {sorted(unexpected)}")
    missing = REQUIRED_TOP_LEVEL_KEYS - set(record)
    if missing:
        _violation(f"missing top-level fields: {sorted(missing)}")

    body = record["body"]
    if body not in {
        "opto-sync state changed",
        "opto-sync sync cycle completed",
        "opto-sync sync cycle failed",
    }:
        _violation("body is not a supported stable event body")
    severity_text = record["severityText"]
    severity_number = record["severityNumber"]
    if severity_text not in SEVERITY_NUMBERS:
        _violation("severityText is not INFO, WARN, or ERROR")
    if type(severity_number) is not int or SEVERITY_NUMBERS[severity_text] != severity_number:
        _violation("severityText and severityNumber do not match")
    _validate_timestamp(record["timestamp"], "timestamp")

    attributes = record["attributes"]
    if not isinstance(attributes, dict):
        _violation("attributes must be an object")
    unexpected_attributes = set(attributes) - ATTRIBUTE_KEYS
    if unexpected_attributes:
        _violation(f"unexpected attributes: {sorted(unexpected_attributes)}")
    missing_attributes = REQUIRED_ATTRIBUTE_KEYS - set(attributes)
    if missing_attributes:
        _violation(f"missing attributes: {sorted(missing_attributes)}")
    if attributes["service.name"] != "opto-sync":
        _violation("service.name must be opto-sync")
    if attributes["opto.sync.schema"] != "opto-sync.telemetry/v1":
        _violation("opto.sync.schema must be opto-sync.telemetry/v1")
    event = attributes["event.name"]
    if event not in EVENTS:
        _violation("event.name is not a supported event kind")
    runtime = attributes["opto.sync.runtime"]
    if runtime not in RUNTIMES:
        _violation("opto.sync.runtime is not typescript, dart, or rust")
    status = attributes["opto.sync.status"]
    if status not in STATUSES:
        _violation("opto.sync.status is not supported")
    _require_exact_int(
        attributes["opto.sync.consecutive_failures"],
        "opto.sync.consecutive_failures",
        0,
        2_147_483_647,
    )

    if "opto.sync.next_retry_at" in attributes:
        _validate_timestamp(attributes["opto.sync.next_retry_at"], "opto.sync.next_retry_at")
    for field in CYCLE_COUNTS:
        if field in attributes:
            _require_exact_int(attributes[field], field, 0, 9_007_199_254_740_991)
    if "opto.sync.has_more_pending" in attributes and type(
        attributes["opto.sync.has_more_pending"]
    ) is not bool:
        _violation("opto.sync.has_more_pending must be a boolean")
    if "error.code" in attributes and (
        not isinstance(attributes["error.code"], str)
        or ERROR_CODE.fullmatch(attributes["error.code"]) is None
    ):
        _violation("error.code must be a stable uppercase code")
    if "request.id" in attributes and (
        not isinstance(attributes["request.id"], str)
        or REQUEST_ID.fullmatch(attributes["request.id"]) is None
    ):
        _violation("request.id must be 8-128 safe identifier characters")

    if event == "opto.sync.state.changed":
        if body != "opto-sync state changed":
            _violation("state event body does not match event.name")
        if (severity_text, severity_number) != STATE_SEVERITIES[status]:
            _violation("state status and severity do not match")
    elif event == "opto.sync.cycle.completed":
        if body != "opto-sync sync cycle completed" or (severity_text, severity_number) != (
            "INFO",
            9,
        ):
            _violation("completed cycle body and severity must be INFO")
        required_cycle_fields = set(CYCLE_COUNTS) | {"opto.sync.has_more_pending"}
        missing_cycle_fields = required_cycle_fields - set(attributes)
        if missing_cycle_fields:
            _violation(f"completed cycle is missing fields: {sorted(missing_cycle_fields)}")
    else:
        if body != "opto-sync sync cycle failed" or (severity_text, severity_number) != (
            "ERROR",
            17,
        ):
            _violation("failed cycle body and severity must be ERROR")
        if "error.code" not in attributes:
            _violation("failed cycle requires error.code")

    if "traceId" in record:
        trace_id = record["traceId"]
        if (
            not isinstance(trace_id, str)
            or TRACE_ID.fullmatch(trace_id) is None
            or trace_id == "0" * 32
        ):
            _violation("traceId must be a non-zero lowercase W3C trace identifier")
    if "spanId" in record:
        span_id = record["spanId"]
        if (
            not isinstance(span_id, str)
            or SPAN_ID.fullmatch(span_id) is None
            or span_id == "0" * 16
        ):
            _violation("spanId must be a non-zero lowercase W3C span identifier")
    if "traceFlags" in record:
        _require_exact_int(record["traceFlags"], "traceFlags", 0, 255)
    if "traceState" in record and (
        not isinstance(record["traceState"], str) or len(record["traceState"]) > 512
    ):
        _violation("traceState must be a string no longer than 512 characters")
