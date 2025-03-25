"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.config import CmdOptions, Config
from youtube_sync.json_util import load_dict

HERE = Path(__file__).parent


CONFIG_JSON_TXT = """
{
    "output": "dst:TorrentBooks/podcast",
    "rclone": {
      "dst": {
        "type": "b2",
        "account": "****",
        "key": "****"
      }
    },
    "channels": [
      {
        "name": "PlandemicSeriesOfficial",
        "source": "rumble",
        "channel_id": "PlandemicSeriesOfficial"
      },
      {
        "name": "RonGibson",
        "source": "brighteon",
        "channel_id": "rongibsonchannel"
      },
      {
        "name": "TheDuran",
        "source": "youtube",
        "channel_id": "@theduran"
      }
    ]
  }
  """


class ConfigJsonTester(unittest.TestCase):
    """Main tester class."""

    def test_json_parsing(self) -> None:
        """Test command line interface (CLI)."""
        data = load_dict(CONFIG_JSON_TXT)
        config = Config.from_dict(data)
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
