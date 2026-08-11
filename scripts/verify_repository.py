#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    "adapters/dart/check.dart",
    "adapters/dart/telemetry.dart",
    "adapters/rust/src/main.rs",
    "adapters/rust/src/telemetry.rs",
    "adapters/typescript/check.mjs",
    "adapters/typescript/telemetry.mjs",
    "contract/opto-sync-envelope.schema.json",
    "contract/opto-sync-sdk-api.schema.json",
    "contract/opto-sync-sdk-api.v1.json",
    "contract/opto-sync-telemetry-event.schema.json",
    "contract/sdk-source-lock.json",
    "contract/source-lock.json",
    "scripts/audit_generated_harness.mjs",
    "scripts/run_cross_language_matrix.mjs",
    "scripts/temporary_rust_workspace.mjs",
    "scripts/verify_merge_options_source.mjs",
    "src/deep_tests/__init__.py",
    "tests/temporary_rust_workspace.test.mjs",
}
missing = sorted(path for path in required if not (ROOT / path).exists())
if missing:
    raise SystemExit(f"missing required paths: {missing}")
if not (ROOT / "tests").is_dir() or not list((ROOT / "tests").glob("test_*.py")):
    raise SystemExit("at least one executable test module is required")

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
    "commit": "8ef3d4bb63738a90b1e3958500578aebb89ee8cc",
    "path": "schema/merge-options.schema.json",
    "id": "https://opto-sync.dev/schema/merge-options.schema.json",
    "sha256": "d5bd069eefc24293e3f8d8e666bdbd1d2461b59853f73c0cea7bb7c0424d7bd8",
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
expected_dependencies = {
    "opto-sync/opto-sync-clients": "^0.2.0",
    "ores-otel/ores-interfaces": "^0.1.0",
    "oresoftware/next-loggers": "^0.1.0",
}
if zed_manifest.get("dependencies") != expected_dependencies:
    raise SystemExit(f"Zed dependency contract drift: {zed_manifest.get('dependencies')}")
if "node --test tests/temporary_rust_workspace.test.mjs" not in zed_manifest.get(
    "develop", {}
).get("commands", []):
    raise SystemExit("Zed develop contract omits the temporary Rust workspace lifecycle test")

sdk_lock = json.loads((ROOT / "contract/sdk-source-lock.json").read_text(encoding="utf-8"))
expected_sdk_source = {
    "repository": "opto-sync/opto-sync-clients",
    "packageCoordinate": "opto-sync/opto-sync-clients",
    "packageVersion": "0.2.0",
    "revision": "98f76600ae402d38e5c812a7ec38d48f7b42000b",
}
if sdk_lock.get("source") != expected_sdk_source:
    raise SystemExit(f"SDK source identity drift: {sdk_lock.get('source')}")
if sdk_lock["source"]["revision"] != source_lock["source"]["revision"]:
    raise SystemExit("envelope and SDK source revisions disagree")
expected_sdk_assets = {
    "schema/opto-sync-sdk-api.schema.json",
    "schema/opto-sync-sdk-api.v1.json",
    "schema/opto-sync-telemetry-event.schema.json",
}
if {asset.get("path") for asset in sdk_lock.get("assets", [])} != expected_sdk_assets:
    raise SystemExit("SDK mirror asset set drift")
for asset in sdk_lock.get("assets", []):
    if not asset.get("path", "").startswith("schema/"):
        raise SystemExit(f"SDK source path escapes schema ownership: {asset.get('path')}")
    mirror = ROOT / asset.get("mirror", "")
    if not mirror.is_relative_to(ROOT / "contract") or not mirror.is_file():
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
if len(sdk_contract.get("operations", [])) < 19:
    raise SystemExit("SDK API contract lost portable operations")
for operation in sdk_contract["operations"]:
    if set(operation.get("bindings", {})) != {"rust", "dart", "typescript"}:
        raise SystemExit(f"SDK operation language parity drift: {operation.get('id')}")
sdk_dependencies = sdk_contract.get("dependencies", {})
if sdk_dependencies.get("sharedInterfaces") != {
    "coordinate": "ores-otel/ores-interfaces",
    "version": "^0.1.0",
}:
    raise SystemExit("SDK shared-interface dependency drift")
if sdk_dependencies.get("structuredLogging") != {
    "coordinate": "oresoftware/next-loggers",
    "version": "^0.1.0",
}:
    raise SystemExit("SDK structured-logging dependency drift")
if sdk_contract.get("telemetry", {}).get("payloadPolicy") != "metadata_only":
    raise SystemExit("SDK telemetry payload policy drift")
print(f"validated {metadata['organization']}/{metadata['repository']} suite={metadata['suite']}")
