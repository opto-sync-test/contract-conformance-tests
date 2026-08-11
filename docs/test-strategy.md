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

## Expansion path

1. Add a versioned adapter for the primary repository contract.
2. Add sanitized golden fixtures owned by the canonical interface repository.
3. Run the same trace against the reference model and implementation.
4. Retain failing seeds as regression tests.
5. Link behavior changes to the matching Linear issue and repository PR.

## Active versioned canaries

The `opto-sync.telemetry/v1` canary vendors the product schema and its synthetic
valid/invalid corpus. A provenance manifest makes every source byte reproducible,
and the standard-library validator independently exercises the privacy, timestamp,
event, severity, request-ID, cycle, and error invariants without network access.
