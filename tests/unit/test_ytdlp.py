"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.ytdlp import yt_dlp_exe

HERE = Path(__file__).parent
TEST_DATA = HERE / "test_data" / "test_sync"


class YtDlpTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        exe = yt_dlp_exe()
        print(exe)
        print("done")


if __name__ == "__main__":
    unittest.main()
