"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.cli.sync_multiple import Args, run

# COMMAND = "youtube-sync"
# --channel-name @CapitalCosm --output "E:\mikeadams\@CapitalCosm\youtube"

HERE = Path(__file__).parent
CONFIG_JSON = HERE / "test_data" / "config.json"

# COMMAND = "youtube-sync --channel-name @CapitalCosm"  # --output E:\mikeadams\@CapitalCosm\youtube"


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


if __name__ == "__main__":
    unittest.main()
