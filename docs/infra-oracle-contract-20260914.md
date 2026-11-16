# Independent infrastructure oracle contract

This sibling test repository treats the production `*-infra` repository as an external authority and certifies only immutable reviewed revisions.

## Admission invariants

- Pin the production PR/head SHA under test.
- For private source repositories, mirror only the required test surface and record every copied file by Git blob SHA.
- Recompute each mirrored blob with `git hash-object` before executing tests.
- Never grant sibling CI write access to production infrastructure.
- Never run `terraform apply` from this test repository.

## Terraform evidence

For every composed environment root, run `terraform fmt -check`, `terraform init -backend=false -input=false`, and `terraform validate`. Preview, staging, and production must remain independent composition roots.

## Provider boundaries

Reusable/provider-native configuration belongs under `modules/`. Supabase uses `modules` as the native working directory with `modules/supabase/`; Neon uses `modules/neon`; each Cloudflare deployable retains its own Wrangler root. `environments/` must not become a second provider-native authority.

A green run certifies only the exact source SHA/blob set recorded by the test. Any source change invalidates prior certification.
