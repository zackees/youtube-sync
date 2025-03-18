"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.ytdlp import yt_dlp_exe, yt_dlp_plugin_dir

HERE = Path(__file__).parent
TEST_DATA = HERE / "test_data" / "test_sync"


# --plugin-dirs


class YtDlpTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        exe = yt_dlp_exe()
        print(exe)
        print("done")

    def test_get_plugin_dir(self) -> None:
        plugin_dir = yt_dlp_plugin_dir()
        print(plugin_dir)
        print("done")


if __name__ == "__main__":
    unittest.main()
