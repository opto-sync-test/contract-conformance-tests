#!/usr/bin/env python3
"""Verify the pinned generic client API against the Opto Sync test contract."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contract" / "client-api-consumer-lock.json"
PRODUCT_CONTRACT_PATH = ROOT / "contract" / "opto-sync-sdk-api.v1.json"
EXPECTED_SOURCE_REVISION = "5bd8e7cf5a107b364cceb550d873ffac827f2e1a"
EXPECTED_SYMBOLS = {
    "OptoSyncClientOptions": ("type", "public"),
    "_OptoSyncRequestContext": ("type", "private"),
    "OptoSyncTransport": ("interface", "public"),
    "_OptoSyncTelemetrySink": ("interface", "private"),
    "OptoSyncClientError": ("type", "public"),
    "OptoSyncClient": ("class", "public"),
    "_OptoSyncRequestBuilder": ("class", "private"),
    "createOptoSyncClient": ("function", "public"),
    "_normalizeOptoSyncBaseUrl": ("function", "private"),
}
EXPECTED_MEMBERS = {
    "OptoSyncTransport.method.send": ("public", True),
    "_OptoSyncTelemetrySink.method.record": ("private", False),
    "OptoSyncClient.constructor.new": ("public", False),
    "OptoSyncClient.method.health": ("public", True),
    "OptoSyncClient.method._request": ("private", True),
    "_OptoSyncRequestBuilder.constructor.new": ("private", False),
    "_OptoSyncRequestBuilder.method.build": ("private", False),
    "createOptoSyncClient.function.createOptoSyncClient": ("public", False),
    "_normalizeOptoSyncBaseUrl.function._normalizeOptoSyncBaseUrl": (
        "private",
        False,
    ),
}
EXPECTED_PRODUCT_OPERATIONS = {
    "queueUpsert",
    "queueDelete",
    "pendingMutations",
    "buildPushRequest",
    "acknowledgePush",
    "pullCheckpoint",
    "installSnapshot",
    "reconcileIncoming",
    "rebasePending",
    "formatHlc",
    "parseHlc",
    "compareHlc",
    "parseEnvelope",
    "auditEnvelopeProvider",
    "protocolSyncCycle",
    "webSocketTransport",
    "createProtocolSyncTelemetryRecord",
    "emitProtocolSyncTelemetry",
}
EXPECTED_ASSETS = {
    "schemas/client-api.schema.json",
    "clients/api-surface.json",
    "clients/.api-surface.sha256",
}
CREDENTIAL_SHAPE = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{20,}|lin_api_[A-Za-z0-9]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}|BEGIN [A-Z ]*PRIVATE KEY",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    raise SystemExit(message)


def exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    observed = set(value)
    if observed != expected:
        fail(
            f"{context} keys drifted: missing={sorted(expected - observed)} "
            f"unexpected={sorted(observed - expected)}"
        )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nested_value(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            fail(f"identity field is unresolved: {dotted_path}")
        value = value[part]
    return value


def member_inventory(symbols: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        symbol_name = symbol["name"]
        if symbol["kind"] == "function":
            key = f"{symbol_name}.function.{symbol_name}"
            inventory[key] = symbol
        for constructor in symbol.get("constructors", []):
            key = f"{symbol_name}.constructor.{constructor.get('name')}"
            if key in inventory:
                fail(f"duplicate callable key: {key}")
            inventory[key] = constructor
        for method in symbol.get("methods", []):
            key = f"{symbol_name}.method.{method.get('name')}"
            if key in inventory:
                fail(f"duplicate callable key: {key}")
            inventory[key] = method
    return inventory


def walk_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def verify_source_revision(source_root: Path) -> None:
    try:
        observed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"cannot resolve immutable source revision: {error}")
    if observed != EXPECTED_SOURCE_REVISION:
        fail(
            "generic client API source revision drift: "
            f"expected={EXPECTED_SOURCE_REVISION} observed={observed}"
        )


def verify_lock_and_assets(source_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    exact_keys(lock, {"schemaVersion", "ticket", "source", "assets"}, "consumer lock")
    if lock["schemaVersion"] != 1 or lock["ticket"] != "DEN-3963":
        fail("consumer lock identity drift")
    if lock["source"] != {
        "repository": "opto-sync/opto-sync-clients",
        "revision": EXPECTED_SOURCE_REVISION,
    }:
        fail(f"consumer source identity drift: {lock['source']}")

    assets = lock["assets"]
    if not isinstance(assets, list) or not assets:
        fail("consumer lock has no assets")
    if {asset.get("path") for asset in assets if isinstance(asset, dict)} != EXPECTED_ASSETS:
        fail("generic client API asset inventory drift")

    documents: dict[str, dict[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            fail("consumer lock assets must be objects")
        exact_keys(
            asset,
            {"path", "sha256", "identityField", "identity"},
            f"asset {asset.get('path', '<unknown>')}",
        )
        relative = Path(asset["path"])
        path = (source_root / relative).resolve()
        if not path.is_relative_to(source_root.resolve()) or not path.is_file():
            fail(f"unsafe or missing source asset: {relative}")
        observed_digest = sha256(path)
        if observed_digest != asset["sha256"]:
            fail(
                f"source asset hash drift for {relative}: "
                f"locked={asset['sha256']} observed={observed_digest}"
            )
        if asset["identityField"] == "raw":
            observed_identity = path.read_text(encoding="utf-8").strip()
        else:
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                fail(f"source asset root must be an object: {relative}")
            documents[asset["path"]] = document
            observed_identity = nested_value(document, asset["identityField"])
        if observed_identity != asset["identity"]:
            fail(
                f"source asset identity drift for {relative}: "
                f"expected={asset['identity']!r} observed={observed_identity!r}"
            )

    return (
        documents["schemas/client-api.schema.json"],
        documents["clients/api-surface.json"],
    )


def verify_schema(schema: dict[str, Any]) -> None:
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("generic client API schema must remain Draft 2020-12")
    if schema.get("$id") != "https://zpkg.tech/schemas/client-api.schema.json":
        fail("generic client API schema identity drift")
    if schema.get("additionalProperties") is not False:
        fail("generic client API schema must reject unknown root fields")
    if set(schema.get("required", [])) != {"schemaVersion", "package", "symbols"}:
        fail("generic client API root requirements drift")
    definitions = schema.get("$defs", {})
    required_definitions = {
        "package",
        "symbol",
        "behavior",
        "auth",
        "documentationId",
        "stability",
        "deprecation",
    }
    if not isinstance(definitions, dict) or not required_definitions.issubset(definitions):
        fail("generic client API schema lost lifecycle/auth/documentation definitions")


def verify_surface(surface: dict[str, Any], source_root: Path) -> None:
    exact_keys(surface, {"$schema", "schemaVersion", "package", "symbols"}, "API surface")
    if surface["$schema"] != "./client-api.schema.json" or surface["schemaVersion"] != 1:
        fail("API surface schema binding drift")
    if surface["package"] != {
        "coordinate": "opto-sync/opto-sync-clients",
        "description": "Canonical polyglot API contract for opto-sync/opto-sync-clients.",
        "interfaces": [
            {
                "coordinate": "opto-sync/opto-sync-interfaces",
                "schemaDialect": "https://json-schema.org/draft/2020-12/schema",
                "versionRequirement": "^0.1.0",
            }
        ],
        "namespace": "OptoSync",
    }:
        fail("API surface package/interface ownership drift")

    surface_path = source_root / "clients" / "api-surface.json"
    fingerprint = (source_root / "clients" / ".api-surface.sha256").read_text(
        encoding="utf-8"
    ).strip()
    if fingerprint != sha256(surface_path):
        fail("checked-in API surface fingerprint does not match source bytes")

    symbols = surface["symbols"]
    if not isinstance(symbols, list) or not symbols:
        fail("API surface symbols must be a nonempty array")
    symbol_names = [symbol.get("name") for symbol in symbols if isinstance(symbol, dict)]
    if len(symbol_names) != len(symbols) or len(symbol_names) != len(set(symbol_names)):
        fail("API surface symbol names are missing or duplicated")
    actual_symbols = {
        symbol["name"]: (symbol.get("kind"), symbol.get("visibility"))
        for symbol in symbols
    }
    if actual_symbols != EXPECTED_SYMBOLS:
        fail(f"public/private symbol inventory drift: {actual_symbols}")
    for name, (_, visibility) in actual_symbols.items():
        if visibility == "public" and name.startswith("_"):
            fail(f"private-style symbol became public: {name}")
        if visibility == "private" and not name.startswith("_"):
            fail(f"private symbol lost its explicit underscore boundary: {name}")

    members = member_inventory(symbols)
    actual_members = {
        key: (member.get("visibility"), member.get("async"))
        for key, member in members.items()
    }
    if actual_members != EXPECTED_MEMBERS:
        fail(f"callable public/private inventory drift: {actual_members}")

    for key, member in members.items():
        async_value = member.get("async")
        if not isinstance(async_value, bool):
            fail(f"{key} async marker must be boolean")
        expected_behavior = "async" if async_value else "sync"
        if member.get("behavior") != expected_behavior:
            fail(f"{key} lifecycle behavior disagrees with its async marker")
        auth = member.get("auth")
        if auth != {"mode": "none", "schemes": [], "scopes": []}:
            fail(f"{key} auth contract drifted: {auth}")
        if member.get("stability") != "stable" or member.get("deprecation") is not None:
            fail(f"{key} stability/deprecation metadata drifted")
        if not isinstance(member.get("documentationId"), str):
            fail(f"{key} lacks a documentation identifier")

    documentation_ids = [
        value["documentationId"]
        for value in walk_objects(surface)
        if "documentationId" in value
    ]
    if len(documentation_ids) != len(set(documentation_ids)):
        fail("API surface documentation identifiers are duplicated")
    encoded = json.dumps(surface, sort_keys=True)
    if CREDENTIAL_SHAPE.search(encoded):
        fail("credential-shaped material entered the generic API surface")


def verify_product_contract(generic_surface: dict[str, Any]) -> None:
    product = json.loads(PRODUCT_CONTRACT_PATH.read_text(encoding="utf-8"))
    operations = product.get("operations")
    if not isinstance(operations, list):
        fail("product SDK operations must be an array")
    operation_ids = [operation.get("id") for operation in operations]
    if len(operation_ids) != len(set(operation_ids)) or set(operation_ids) != EXPECTED_PRODUCT_OPERATIONS:
        fail(f"product SDK operation inventory drift: {operation_ids}")
    for operation in operations:
        if set(operation.get("bindings", {})) != {"rust", "dart", "typescript"}:
            fail(f"cross-language bindings drift: {operation.get('id')}")
        if operation.get("conformance") not in {"portable", "candidate"}:
            fail(f"unknown operation conformance: {operation.get('id')}")
    if product.get("telemetry", {}).get("payloadPolicy") != "metadata_only":
        fail("product telemetry must remain metadata-only")

    generic_callables = {
        member.get("name")
        for member in member_inventory(generic_surface["symbols"]).values()
    }
    collisions = generic_callables & EXPECTED_PRODUCT_OPERATIONS
    if collisions:
        fail(
            "generic construction/transport shell shadows product operations: "
            f"{sorted(collisions)}"
        )


def main() -> None:
    source_value = os.environ.get("OPTO_SYNC_CLIENTS_DIR", "").strip()
    if not source_value:
        fail("OPTO_SYNC_CLIENTS_DIR must point to the immutable primary checkout")
    source_root = Path(source_value).resolve()
    if not source_root.is_dir():
        fail(f"OPTO_SYNC_CLIENTS_DIR is not a directory: {source_root}")

    verify_source_revision(source_root)
    schema, surface = verify_lock_and_assets(source_root)
    verify_schema(schema)
    verify_surface(surface, source_root)
    verify_product_contract(surface)
    print(
        "validated DEN-3963 generic consumer canary: "
        "9 symbols, 9 callables, 18 Rust/Dart/TypeScript product operations"
    )


if __name__ == "__main__":
    main()
