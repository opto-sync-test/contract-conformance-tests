import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generated_evidence_hygiene",
    ROOT / "scripts" / "check_generated_evidence_hygiene.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class GeneratedEvidenceHygieneTests(unittest.TestCase):
    def test_transient_outputs_are_rejected(self):
        paths = [
            ".typespec-json-schema-validator/contract-ir.json",
            "report.sarif",
            "tmp/tjsv/report.json",
        ]
        self.assertEqual(MODULE.find_violations(paths), sorted(paths))

    def test_fixtures_are_allowed(self):
        paths = [
            "fixtures/contract-ir.json",
            "tests/fixtures/report.sarif",
            "testdata/generated.schema.json",
        ]
        self.assertEqual(MODULE.find_violations(paths), [])

    def test_repository_is_clean(self):
        self.assertEqual(MODULE.find_violations(MODULE.tracked_files()), [])
