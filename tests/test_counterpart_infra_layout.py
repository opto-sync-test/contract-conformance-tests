import pathlib
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE_REPO = "https://github.com/opto-sync/opto-sync-infra.git"
SOURCE_SHA = "36c457fe003b9c844035961f035bf80d55aba2dd"
ENVIRONMENTS = ("preview", "staging", "production")
PROVIDER_NATIVE_NAMES = {"wrangler.toml", "wrangler.json", "wrangler.jsonc", "neon.ts"}

def run(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

@unittest.skipUnless(shutil.which("terraform"), "Terraform is exercised by the dedicated infra counterpart workflow")
class CounterpartInfraLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="opto-infra-contract-")
        cls.root = pathlib.Path(cls._tmp.name) / "infra"
        cls.root.mkdir()
        run("git", "init", "-q", cwd=cls.root)
        run("git", "remote", "add", "origin", SOURCE_REPO, cwd=cls.root)
        run("git", "fetch", "--depth=1", "origin", SOURCE_SHA, cwd=cls.root)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=cls.root)
        cls.manifest = tomllib.loads((cls.root / ".ores-infra.toml").read_text())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_modules_first_provider_roots(self) -> None:
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["layout"], "modules")
        self.assertEqual(self.manifest["modules_root"], "modules")
        self.assertEqual(self.manifest["environments_root"], "environments")
        providers = self.manifest["providers"]
        self.assertEqual(providers["supabase"]["canonical_path"], "modules/supabase")
        self.assertEqual(providers["supabase"]["native_working_directory"], "modules")
        self.assertEqual(providers["cloudflare"]["canonical_path"], "modules/cloudflare")
        self.assertEqual(providers["neon"]["project_root"], "modules/neon")
        self.assertEqual(providers["neon"]["config"], "modules/neon/neon.ts")
        self.assertEqual(self.manifest["policy"]["state_isolation"], "per-provider-per-environment")

    def test_environment_roots_format_init_validate(self) -> None:
        run("terraform", "fmt", "-check", "-recursive", "modules/cloudflare/terraform", cwd=self.root)
        seen = set()
        for environment in ENVIRONMENTS:
            env_root = self.root / "environments" / environment
            text = (env_root / "main.tf").read_text()
            self.assertIn('backend "s3" {}', text)
            self.assertRegex(text, r'source\s*=\s*"\.\./\.\./modules/cloudflare/terraform/worker-shell"')
            self.assertRegex(text, rf'environment\s*=\s*"{re.escape(environment)}"')
            seen.add(environment)
            run("terraform", "fmt", "-check", "-recursive", ".", cwd=env_root)
            run("terraform", "init", "-backend=false", "-input=false", cwd=env_root)
            run("terraform", "validate", "-no-color", cwd=env_root)
        self.assertEqual(seen, set(ENVIRONMENTS))

    def test_environments_do_not_commit_provider_native_source_or_state(self) -> None:
        tracked = run("git", "ls-files", "environments", cwd=self.root).stdout.splitlines()
        self.assertTrue(tracked)
        for relative in tracked:
            path = pathlib.PurePosixPath(relative)
            self.assertNotIn(path.name, PROVIDER_NATIVE_NAMES, relative)
            self.assertNotIn("supabase", path.parts, relative)
            self.assertFalse(path.name.endswith(".tfstate"), relative)
            self.assertNotIn(".terraform", path.parts, relative)

    def test_worker_shell_is_opt_in(self) -> None:
        module_text = (self.root / "modules/cloudflare/terraform/worker-shell/main.tf").read_text()
        self.assertIn('variable "enabled"', module_text)
        self.assertIn("default = false", module_text)
        self.assertIn("count", module_text)
        self.assertIn("var.enabled ? 1 : 0", module_text)

if __name__ == "__main__":
    unittest.main()
