#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SOURCE_REVISION = "9c3690e3c5cb445100daaffd6729b6ed6b25217d"
metadata = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
required = {
    "README.md",
    "AGENTS.md",
    "project.json",
    "pyproject.toml",
    ".zpkg.toml",
    "docs/test-strategy.md",
    "scripts/verify_repository.py",
    ".github/workflows/deep-tests.yml",
    *metadata.get("required_paths", []),
}
missing = sorted(path for path in required if not (ROOT / path).exists())
if missing:
    raise SystemExit(f"missing required paths: {missing}")
if not (ROOT / "tests").is_dir() or not list((ROOT / "tests").glob("test_*.py")):
    raise SystemExit("at least one executable test module is required")

contract_root = ROOT / "contracts" / "opto-sync-telemetry" / "v1"
provenance = json.loads((contract_root / "provenance.json").read_text(encoding="utf-8"))
source = provenance.get("source", {})
if provenance.get("manifest_version") != 1 or provenance.get("contract") != "opto-sync.telemetry/v1":
    raise SystemExit("telemetry provenance identity drift")
if provenance.get("product_version") != "0.3.0":
    raise SystemExit("telemetry product version drift")
if source.get("repository") != "opto-sync/opto-sync-clients":
    raise SystemExit("telemetry source repository drift")
if source.get("commit") != CLIENT_SOURCE_REVISION:
    raise SystemExit("telemetry source commit drift")

entries = provenance.get("files")
if not isinstance(entries, list) or not entries:
    raise SystemExit("telemetry provenance has no files")
listed = [entry.get("vendored_path") for entry in entries if isinstance(entry, dict)]
if len(listed) != len(entries) or len(set(listed)) != len(listed):
    raise SystemExit("telemetry provenance paths are missing or duplicated")
actual = {
    path.relative_to(contract_root).as_posix()
    for path in contract_root.rglob("*.json")
    if path.name != "provenance.json"
}
if set(listed) != actual:
    raise SystemExit(f"telemetry provenance inventory drift: listed={sorted(listed)} actual={sorted(actual)}")
for entry in entries:
    relative = Path(entry["vendored_path"])
    vendored = (contract_root / relative).resolve()
    if not vendored.is_relative_to(contract_root.resolve()) or not vendored.is_file():
        raise SystemExit(f"unsafe or missing telemetry provenance path: {relative}")
    expected_digest = entry.get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise SystemExit(f"invalid telemetry provenance digest: {relative}")
    digest = hashlib.sha256(vendored.read_bytes()).hexdigest()
    if digest != expected_digest:
        raise SystemExit(f"telemetry provenance hash mismatch: {relative}")

marker = re.compile(r"^(<{7}|={7}|>{7})", re.MULTILINE)
credential = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|lin_api_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY")
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or path.stat().st_size > 1_000_000:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if marker.search(text):
        raise SystemExit(f"unresolved conflict marker: {path.relative_to(ROOT)}")
    if credential.search(text):
        raise SystemExit(f"credential-shaped content: {path.relative_to(ROOT)}")

agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
for phrase in ("merge base", "3–10 relevant commits", "ours", "theirs", "Fail closed"):
    if phrase not in agents:
        raise SystemExit(f"semantic conflict policy missing phrase: {phrase}")

workflow = (ROOT / ".github/workflows/deep-tests.yml").read_text(encoding="utf-8")
if "permissions:\n  contents: read" not in workflow or "pull_request_target" in workflow:
    raise SystemExit("workflow permission boundary is unsafe")
action_pattern = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
actions = [line.split("uses:", 1)[1].strip() for line in workflow.splitlines() if "uses:" in line]
if len(actions) < 2 or any(not action_pattern.fullmatch(action) for action in actions):
    raise SystemExit(f"workflow actions are not immutably pinned: {actions}")
if "node --test tests/temporary_rust_workspace.test.mjs" not in workflow:
    raise SystemExit("temporary Rust workspace lifecycle test is not wired into CI")

if metadata.get("bootstrap_operation") != "deep-test-fleet-20260808":
    raise SystemExit("bootstrap operation identity drift")
if not str(metadata.get("organization", "")).endswith("-test"):
    raise SystemExit("repository is not bound to a test organization")

source_lock = json.loads((ROOT / "contract/source-lock.json").read_text(encoding="utf-8"))
schema_bytes = (ROOT / "contract/opto-sync-envelope.schema.json").read_bytes()
schema = json.loads(schema_bytes)
schema_digest = hashlib.sha256(schema_bytes).hexdigest()
if schema_digest != source_lock["source"]["sha256"]:
    raise SystemExit(
        f"vendored schema digest drift: locked={source_lock['source']['sha256']} actual={schema_digest}"
    )
if schema.get("$id") != source_lock["source"]["id"]:
    raise SystemExit("vendored schema $id drift")
if not re.fullmatch(r"[0-9a-f]{40}", source_lock["source"].get("revision", "")):
    raise SystemExit("authoritative schema source must be pinned to a full commit SHA")
if f"ref: {source_lock['source']['revision']}" not in workflow:
    raise SystemExit("polyglot workflow source revision drift")

merge_source = {
    "repository": "opto-sync/syncer.rs",
    "commit": "bb71ac1b4b7d94dd7035e6cc7b76e5c10f284e98",
    "path": "schema/merge-options.schema.json",
    "id": "https://opto-sync.dev/schema/merge-options.schema.json",
    "sha256": "e9107667cee2868a922a70c9c48175c62b466fa728466c23bac766aebcbb2f2a",
    "status": "canonical",
    "blockers": [],
}
required_merge_workflow_fragments = (
    "repository: opto-sync/syncer.rs",
    f"ref: {merge_source['commit']}",
    "path: .source/syncer-rs",
    "node scripts/verify_merge_options_source.mjs",
)
for fragment in required_merge_workflow_fragments:
    if fragment not in workflow:
        raise SystemExit(f"merge-options workflow provenance drift: missing {fragment}")

zed_manifest = tomllib.loads((ROOT / ".zpkg.toml").read_text(encoding="utf-8"))
if zed_manifest.get("package", {}).get("org") != "opto-sync-test":
    raise SystemExit("Zed package organization drift")
if zed_manifest.get("dependencies", {}):
    raise SystemExit(
        "test package must not declare unreleased clients/Ores Zed dependencies"
    )
if "node --test tests/temporary_rust_workspace.test.mjs" not in zed_manifest.get(
    "develop", {}
).get("commands", []):
    raise SystemExit("Zed develop contract omits the temporary Rust workspace lifecycle test")

sdk_lock = json.loads((ROOT / "contract/sdk-source-lock.json").read_text(encoding="utf-8"))
expected_sdk_source = {
    "repository": "opto-sync/opto-sync-clients",
    "packageCoordinate": "opto-sync/opto-sync-clients",
    "packageVersion": "0.3.0",
    "revision": CLIENT_SOURCE_REVISION,
}
if sdk_lock.get("source") != expected_sdk_source:
    raise SystemExit(f"SDK source identity drift: {sdk_lock.get('source')}")
if sdk_lock["source"]["revision"] != source_lock["source"]["revision"]:
    raise SystemExit("envelope and SDK source revisions disagree")
expected_sdk_assets = {
    "schema/opto-sync-sdk-api.schema.json",
    "schema/opto-sync-sdk-api.v1.json",
    "schema/opto-sync-sdk-values.v1.schema.json",
    "schema/opto-sync-telemetry-event.schema.json",
    "schema/opto-sync-telemetry.schema.json",
}
if {asset.get("path") for asset in sdk_lock.get("assets", [])} != expected_sdk_assets:
    raise SystemExit("SDK mirror asset set drift")
for asset in sdk_lock.get("assets", []):
    if not asset.get("path", "").startswith("schema/"):
        raise SystemExit(f"SDK source path escapes schema ownership: {asset.get('path')}")
    mirror = (ROOT / asset.get("mirror", "")).resolve()
    allowed_mirror_roots = ((ROOT / "contract").resolve(), contract_root.resolve())
    if not any(mirror.is_relative_to(root) for root in allowed_mirror_roots) or not mirror.is_file():
        raise SystemExit(f"SDK mirror path is invalid: {asset.get('mirror')}")
    contents = mirror.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()
    if digest != asset.get("sha256"):
        raise SystemExit(
            f"SDK mirror digest drift for {asset.get('mirror')}: locked={asset.get('sha256')} actual={digest}"
        )
    document = json.loads(contents)
    if document.get(asset.get("identityField")) != asset.get("identity"):
        raise SystemExit(f"SDK mirror identity drift for {asset.get('mirror')}")

sdk_contract = json.loads((ROOT / "contract/opto-sync-sdk-api.v1.json").read_text(encoding="utf-8"))
if sdk_contract.get("mergeOptionsSchema") != merge_source:
    raise SystemExit("SDK merge-options schema ownership drift")
operations = sdk_contract.get("operations", [])
operation_ids = [operation.get("id") for operation in operations]
expected_operation_ids = {
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
if len(operations) != 18 or set(operation_ids) != expected_operation_ids:
    raise SystemExit(f"SDK API operation inventory drift: {operation_ids}")
if len(operation_ids) != len(set(operation_ids)):
    raise SystemExit("SDK API operation ids are duplicated")
expected_portable = {
    "formatHlc",
    "parseHlc",
    "compareHlc",
    "parseEnvelope",
    "createProtocolSyncTelemetryRecord",
    "emitProtocolSyncTelemetry",
}
actual_portable = {
    operation["id"]
    for operation in operations
    if operation.get("conformance") == "portable"
}
if actual_portable != expected_portable:
    raise SystemExit(f"portable SDK operation classification drift: {actual_portable}")
values_schema = json.loads(
    (ROOT / "contract/opto-sync-sdk-values.v1.schema.json").read_text(encoding="utf-8")
)
values_prefix = f"{values_schema['$id']}#/$defs/"
for operation in operations:
    if set(operation.get("bindings", {})) != {"rust", "dart", "typescript"}:
        raise SystemExit(f"SDK operation language parity drift: {operation.get('id')}")
    conformance = operation.get("conformance")
    if conformance == "candidate" and not operation.get("differences"):
        raise SystemExit(f"candidate SDK operation lacks differences: {operation.get('id')}")
    if conformance not in {"portable", "candidate"}:
        raise SystemExit(f"unknown SDK conformance state: {operation.get('id')}")
    normalized = operation.get("normalized", {})
    refs = (
        [normalized.get("requestSchemaRef"), normalized.get("resultSchemaRef")]
        if normalized.get("kind") == "call"
        else [normalized.get("contractSchemaRef")]
    )
    for reference in refs:
        if not isinstance(reference, str) or not reference.startswith(values_prefix):
            raise SystemExit(f"SDK normalized reference drift: {operation.get('id')} {reference}")
        definition = reference.removeprefix(values_prefix)
        if definition not in values_schema.get("$defs", {}):
            raise SystemExit(f"SDK normalized reference is unresolved: {reference}")
sdk_dependencies = sdk_contract.get("dependencies", {})
if sdk_dependencies.get("sharedInterfaces") != {
    "coordinate": "ores-otel/ores-interfaces",
    "version": "^0.1.0",
    "status": "pending-release",
    "integration": "injected",
}:
    raise SystemExit("SDK shared-interface dependency drift")
if sdk_dependencies.get("structuredLogging") != {
    "coordinate": "oresoftware/next-loggers",
    "version": "^0.1.0",
    "status": "pending-release",
    "integration": "injected",
}:
    raise SystemExit("SDK structured-logging dependency drift")
if sdk_contract.get("telemetry", {}).get("payloadPolicy") != "metadata_only":
    raise SystemExit("SDK telemetry payload policy drift")
if sdk_contract.get("telemetry", {}).get("eventSchema") != {
    "path": "schema/opto-sync-telemetry.schema.json",
    "id": "https://opto-sync.dev/schema/opto-sync-telemetry.v1.schema.json",
}:
    raise SystemExit("SDK telemetry schema reference drift")
if provenance["source"]["commit"] != sdk_lock["source"]["revision"]:
    raise SystemExit("telemetry and SDK provenance revisions disagree")
telemetry_alias = json.loads(
    (ROOT / "contract/opto-sync-telemetry-event.schema.json").read_text(encoding="utf-8")
)
if telemetry_alias.get("deprecated") is not True or telemetry_alias.get("$ref") != (
    "https://opto-sync.dev/schema/opto-sync-telemetry.v1.schema.json"
):
    raise SystemExit("legacy telemetry identifier is not a deprecated canonical alias")
print(f"validated {metadata['organization']}/{metadata['repository']} suite={metadata['suite']}")
