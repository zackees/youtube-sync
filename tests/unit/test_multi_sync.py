"""
Unit test file.
"""

import json
import os
import unittest
from pathlib import Path

from youtube_sync.cli.sync_multiple import Args, run

HERE = Path(__file__).parent
CONFIG_JSON = HERE / "test_data" / "config.json"


class MainTester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        """Test command line interface (CLI)."""
        self.assertTrue(CONFIG_JSON.exists())

    def test_basic(self) -> None:
        """Test command line interface (CLI)."""
        args = Args(
            config=CONFIG_JSON,
            dry_run=True,
        )
        run(args)

    def test_from_env(self) -> None:
        """Test command line interface (CLI)."""
        one_line_json_str = json.dumps(json.loads(CONFIG_JSON.read_text()))
        os.environ["YOUTUBE_SYNC_CONFIG_JSON"] = one_line_json_str
        args = Args(
            config=None,
            dry_run=True,
        )
        run(args)


if __name__ == "__main__":
    unittest.main()
