import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContractAssetTests(unittest.TestCase):
    def test_vendored_schema_matches_locked_identity_and_digest(self) -> None:
        source_lock = json.loads(
            (ROOT / "contract/source-lock.json").read_text(encoding="utf-8")
        )
        schema_bytes = (ROOT / "contract/opto-sync-envelope.schema.json").read_bytes()
        schema = json.loads(schema_bytes)
        self.assertEqual(schema["$id"], source_lock["source"]["id"])
        self.assertEqual(
            hashlib.sha256(schema_bytes).hexdigest(), source_lock["source"]["sha256"]
        )

    def test_fixture_matrix_is_nontrivial_and_balanced(self) -> None:
        fixture_lock = json.loads(
            (ROOT / "contract/source-lock.json").read_text(encoding="utf-8")
        )["fixtures"]
        self.assertGreaterEqual(fixture_lock["validCount"], 8)
        self.assertGreaterEqual(fixture_lock["invalidCount"], 8)

    def test_sdk_and_telemetry_mirrors_match_locked_digests(self) -> None:
        source_lock = json.loads(
            (ROOT / "contract/sdk-source-lock.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            source_lock["source"]["revision"],
            "55ffb2e922785b12d68be44ae256ff61a497f8a1",
        )
        for asset in source_lock["assets"]:
            contents = (ROOT / asset["mirror"]).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), asset["sha256"])
            document = json.loads(contents)
            self.assertEqual(document[asset["identityField"]], asset["identity"])

    def test_sdk_contract_has_rust_dart_typescript_and_ores_parity(self) -> None:
        contract = json.loads(
            (ROOT / "contract/opto-sync-sdk-api.v1.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(len(contract["operations"]), 19)
        self.assertEqual(
            contract["mergeOptionsSchema"],
            {
                "repository": "opto-sync/syncer.rs",
                "commit": "8ef3d4bb63738a90b1e3958500578aebb89ee8cc",
                "path": "schema/merge-options.schema.json",
                "id": "https://opto-sync.dev/schema/merge-options.schema.json",
                "sha256": "d5bd069eefc24293e3f8d8e666bdbd1d2461b59853f73c0cea7bb7c0424d7bd8",
            },
        )
        for operation in contract["operations"]:
            self.assertEqual(set(operation["bindings"]), {"rust", "dart", "typescript"})
        self.assertEqual(
            contract["dependencies"]["sharedInterfaces"]["coordinate"],
            "ores-otel/ores-interfaces",
        )
        self.assertEqual(
            contract["dependencies"]["structuredLogging"]["coordinate"],
            "oresoftware/next-loggers",
        )
        self.assertEqual(contract["telemetry"]["payloadPolicy"], "metadata_only")

    def test_merge_options_source_gate_is_immutably_wired(self) -> None:
        workflow = (ROOT / ".github/workflows/deep-tests.yml").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "repository: opto-sync/syncer.rs",
            "ref: 8ef3d4bb63738a90b1e3958500578aebb89ee8cc",
            "path: .source/syncer-rs",
            "node scripts/verify_merge_options_source.mjs",
        ):
            self.assertIn(fragment, workflow)


if __name__ == "__main__":
    unittest.main()
