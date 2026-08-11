# Deep test strategy

## Scope

Suite: `contract`
Test organization: `opto-sync-test`
Primary organization: `opto-sync`

## Invariants

- every randomized test uses an explicit deterministic seed;
- retries, duplicates, migrations, and rejected inputs are observable assertions, not sleeps;
- test data is synthetic and contains no production credentials or customer payloads;
- the suite runs without network access by default;
- a product adapter must preserve the reference model and publish the seed and minimized trace on failure;
- scheduled CI is defense in depth; pull-request and main-branch checks remain authoritative.
- the authoritative envelope schema remains owned by `opto-sync/opto-sync-clients`;
  this test repository keeps only a byte-identical, revision-and-digest-locked mirror;
- Rust, TypeScript, and Dart decisions are produced by their production client
  APIs, never by test-only reimplementations of the schema;
- conformance output records fixture identifiers and decisions only; customer
  payloads and raw documents are never logged.
- structured logging stays injection-only: Rust, Dart, and TypeScript must emit
  one identical closed telemetry shape, reject sensitive fields, and preserve
  sync results when a logger fails or panics;
- the client SDK merge-options reference must resolve to the exact clean
  `opto-sync/syncer.rs` commit, schema digest, and `$id` recorded in the manifest;
- generated fleet validators are not sufficient evidence by themselves: the
  committed mode-160000 gitlink must equal the SHA in `source-pins.json`.
  `scripts/audit_generated_harness.mjs` checks that invariant without editing
  generator-owned repositories.

## Expansion path

1. Advance `contract/source-lock.json` only after reviewing the authoritative source change.
2. Run the same sanitized source-owned fixture corpus through every production adapter.
3. Run the same trace against the reference model and implementation.
4. Retain failing seeds as regression tests.
5. Link behavior changes to the matching Linear issue and repository PR.
