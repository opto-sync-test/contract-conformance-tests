# Opto-Sync telemetry contract canary

This repository vendors the privacy-bounded `opto-sync.telemetry/v1` contract from
`opto-sync/opto-sync-clients` so the test organization can detect cross-language
contract drift without network access or product credentials.

## Pinned source

The authoritative byte-level provenance is
`contracts/opto-sync-telemetry/v1/provenance.json`. It pins product version `0.3.0`,
the exact product commit, every upstream source path, and the SHA-256 digest of the
vendored schema and fixture files. PR #82 established the privacy-bounded wire
contract; its SDK/API reconciliation and final source pin are reviewed in
[opto-sync-clients PR #83](https://github.com/opto-sync/opto-sync-clients/pull/83).

The canary intentionally vendors files instead of fetching them in CI. Updating the
contract requires one focused pull request that changes the files and provenance
together; an unrecorded byte change fails repository verification.

## What the canary checks

The dependency-free validator and corpus tests enforce:

- the expected valid and invalid upstream fixtures;
- exact manifest hashes and a closed schema/attribute boundary;
- canonical millisecond UTC timestamps that are real calendar dates;
- runtime, event kind, status, body, and OpenTelemetry severity relationships;
- cycle counters, retry metadata, stable error codes, and safe request IDs;
- rejection of raw records, payloads, checkpoints, mutations, messages, stack traces,
  request bodies, response bodies, and database statements.

The Python validator mirrors the constraints exercised by this contract corpus. The
vendored JSON Schema remains authoritative for consumers using a full Draft 2020-12
implementation.

## Run locally

```bash
PYTHONPATH=src python -m unittest tests.test_telemetry_contract -v
python scripts/verify_repository.py
```
