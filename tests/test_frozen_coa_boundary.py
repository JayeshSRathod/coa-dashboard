import subprocess
import unittest
from pathlib import Path


class FrozenCOABoundaryTests(unittest.TestCase):
    """Protect the agreed frozen COA v1 source on repository-backed test runs."""

    def test_frozen_coa_math_git_blob_is_baseline(self):
        if not Path(".git").exists():
            self.skipTest("source archive has no Git metadata")
        actual = subprocess.check_output(
            ["git", "hash-object", "engine/coa_math.py"], text=True
        ).strip()
        self.assertEqual(actual, "3bb6452d2eddfb7898f4e3a554af14f8881b2ecf")


if __name__ == "__main__":
    unittest.main()
