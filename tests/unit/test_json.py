"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.config import CmdOptions, Config

HERE = Path(__file__).parent
CONFIG_JSON = HERE / "test_data" / "config.json"


class ConfigJsonTester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        """Test command line interface (CLI)."""
        self.assertTrue(CONFIG_JSON.exists())

    def test_json_parsing(self) -> None:
        """Test command line interface (CLI)."""

        config = Config.from_file(CONFIG_JSON)
        self.assertIsInstance(config, Config)
        assert isinstance(config, Config)
        self.assertEqual(config.output, "dst:TorrentBooks/podcast")
        self.assertIsInstance(config.rclone, dict)
        self.assertIsInstance(config.channels, list)
        self.assertEqual(len(config.channels), 3)
        self.assertIsInstance(config.cmd_options, CmdOptions)
        self.assertTrue(config.cmd_options.download)
        self.assertTrue(config.cmd_options.scan)


if __name__ == "__main__":
    unittest.main()
