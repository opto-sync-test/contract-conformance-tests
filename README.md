# opto-sync-test/contract-conformance-tests

Deterministic state-model, idempotency, serialization, and protocol contract conformance tests.

This repository is the `contract` deep-test suite for `opto-sync`. It is intentionally dependency-light and deterministic so failures can be reproduced locally without production credentials or customer data.

## Run

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
node --test tests/temporary_rust_workspace.test.mjs
python scripts/verify_repository.py
```

The repository also carries an exact, digest-locked mirror of the authoritative
`opto-sync/opto-sync-clients/schema/opto-sync-envelope.schema.json`. The mirror
does not redefine the contract: `contract/source-lock.json` records its owning
repository, full revision, path, `$id`, and SHA-256 digest.

The portable SDK API meta-schema, v1 API instance, normalized-values schema,
and canonical privacy-bounded telemetry schema are mirrored the same way.
`contract/sdk-source-lock.json` records their owning package coordinate,
version and full revision, authoritative paths, identities, and SHA-256
digests. Repository verification fails closed on any byte, operation,
language-binding, Ores release-state, or telemetry-policy drift.
CI separately checks out `opto-sync/syncer.rs` at the exact commit recorded by
the SDK manifest and verifies its owned merge-options schema bytes and `$id`:

```bash
SYNCER_RS_DIR=/path/to/syncer.rs node scripts/verify_merge_options_source.mjs
```

To exercise the production validators over the authoritative valid/invalid
fixture corpus:

```bash
OPTO_SYNC_CLIENTS_DIR=/path/to/opto-sync-clients \
  node scripts/run_cross_language_matrix.mjs --prepare --require-telemetry
```

The runner builds and calls the existing Rust `parse_envelope`, TypeScript
`parseEnvelope`, and Dart `parseEnvelope` APIs. It also executes the shared HLC
format/parse/compare vector, builds the canonical Ores/OpenTelemetry record,
and sends it through each runtime's fail-open sink. It fails if any runtime
differs from the fixture classification, another runtime, the pinned schema
bytes, or the pinned source revision. Each runtime keeps its truthful
`opto.sync.runtime` attribute; only that field is normalized for cross-language
comparison. CI also runs each SDK's sink-failure and sensitive-field tests when
`--require-telemetry` is selected. The default mode still enforces all 25
envelope fixtures. For local
evaluation of an uncommitted upstream branch only, set
`OPTO_SYNC_ALLOW_UNPINNED_SOURCE=1`; CI never uses that escape hatch.

The intended opto-sync and Ores package coordinates remain recorded in the SDK
contract as injected, `pending-release` metadata. `.zpkg.toml` deliberately
declares no unresolved dependency; a synthetic registry is not release
provenance.

Generated fleet repositories can be audited without editing their generated
plans. This command fails if `source-pins.json` names a different commit than
the repository's mode-160000 gitlink:

```bash
node scripts/audit_generated_harness.mjs ../rust-engine-e2e ../typescript-client-e2e ../dart-client-e2e
```

## Versioned product canaries

The [`opto-sync.telemetry/v1` canary](docs/opto-sync-telemetry-canary.md) vendors the
privacy-bounded telemetry schema and sanitized corpus from `opto-sync-clients`. Its
provenance manifest pins product version `0.3.0`, the exact source commit and paths,
and SHA-256 hashes, while dependency-free tests enforce the cross-language contract.

Tracking: https://github.com/ORESoftware/ai-agent-coordinator.rs/issues/139
