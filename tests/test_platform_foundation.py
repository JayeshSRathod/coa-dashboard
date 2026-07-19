import tempfile
import unittest
from pathlib import Path

from src.common.config import Settings
from src.persistence.connection import connect
from src.persistence.migration import apply_migrations


class PlatformFoundationTests(unittest.TestCase):
    def test_settings_respect_supplied_root(self):
        root = Path(tempfile.mkdtemp())
        settings = Settings.from_environment(root)
        self.assertEqual(settings.data_dir, root / "data")

    def test_connection_and_empty_migrations(self):
        root = Path(tempfile.mkdtemp())
        with connect(root / "research.db") as connection:
            apply_migrations(connection, [])
            self.assertEqual(connection.execute("SELECT 1").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
