import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_SH = PROJECT_ROOT / "run.sh"


@unittest.skipUnless(shutil.which("conda"), "conda not available")
class LauncherTest(unittest.TestCase):
    """Verifies run.sh resolves the project root through symlinks and cwd.

    Uses ``--help`` (argparse exits before QApplication), so no display is
    needed while still proving ``src/main.py`` was found.
    """

    def _run(self, argv, cwd) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=90,
        )

    def _assert_usage(self, result: subprocess.CompletedProcess) -> None:
        output = (result.stdout + result.stderr).lower()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage", output)

    def test_direct_invocation(self):
        self._assert_usage(self._run(["bash", str(RUN_SH), "--help"], PROJECT_ROOT))

    def test_symlink_from_project_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "pet"
            os.symlink(RUN_SH, link)
            self._assert_usage(self._run([str(link), "--help"], tmp))

    def test_symlink_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "pet"
            os.symlink(RUN_SH, link)
            self._assert_usage(self._run([str(link), "--help"], Path.home()))

    def test_relative_symlink_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "pet"
            os.symlink(os.path.relpath(RUN_SH, tmp), link)
            self._assert_usage(self._run(["./pet", "--help"], tmp))

    def test_arguments_passed_through(self):
        result = self._run(["bash", str(RUN_SH), "--help"], PROJECT_ROOT)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ("--move", "--speed", "--run-seconds", "--screenshot-seq"):
            self.assertIn(flag, output)


if __name__ == "__main__":
    unittest.main()
