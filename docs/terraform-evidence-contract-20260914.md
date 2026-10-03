# Terraform evidence contract

Sibling infrastructure tests must produce executable Terraform evidence rather than infer correctness from folder names.

## Required checks

1. `terraform fmt -check -recursive` over reusable Terraform modules.
2. `terraform fmt -check -recursive .` in every environment root.
3. `terraform init -backend=false -input=false` so remote state is never touched.
4. `terraform validate -no-color` for preview, staging, and production.
5. Inspect Git-tracked files, not generated working directories, when rejecting `.terraform/`, `*.tfstate`, and duplicated provider-native source.

## Failure classification

A missing runner, denied private-repository checkout, or zero-step job is admission/runner failure, not proof that the Terraform passed or failed. Formatting and validation failures reached after setup are source findings and must be fixed in the production `*-infra` PR before the oracle is repinned.

The evidence is revision-specific and must be regenerated whenever the production source head changes.
