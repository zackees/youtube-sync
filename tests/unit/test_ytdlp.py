"""
Unit test file.
"""

import unittest
from typing import Any

from youtube_sync import Source
from youtube_sync.ytdlp.ytdlp import YtDlp

VID_URL = "https://www.youtube.com/watch?v=XfELJU1mRMg"


class YtDlpTester(unittest.TestCase):
    """Main tester class."""

    def test_ytdlp(self) -> None:
        ytdlp = YtDlp(Source.YOUTUBE)
        info: Any = ytdlp.fetch_channel_url(VID_URL)
        print(info)
        info = ytdlp.fetch_video_info(VID_URL)
        print(info)
        info = ytdlp.fetch_channel_id(VID_URL)
        print(info)


if __name__ == "__main__":
    unittest.main()
