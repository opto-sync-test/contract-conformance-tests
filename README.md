# opto-sync-test/contract-conformance-tests

Deterministic state-model, idempotency, serialization, and protocol contract conformance tests.

This repository is the `contract` deep-test suite for `opto-sync`. It is intentionally dependency-light and deterministic so failures can be reproduced locally without production credentials or customer data.

## Run

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/verify_repository.py
```

The initial model is executable rather than a placeholder. Product adapters should be added through focused pull requests while preserving the reference-model tests as an oracle.

## Versioned product canaries

The [`opto-sync.telemetry/v1` canary](docs/opto-sync-telemetry-canary.md) vendors the
privacy-bounded telemetry schema and sanitized corpus from `opto-sync-clients`. Its
provenance manifest pins product version `0.3.0`, the exact source commit and paths,
and SHA-256 hashes, while dependency-free tests enforce the cross-language contract.

Tracking: https://github.com/ORESoftware/ai-agent-coordinator.rs/issues/139
