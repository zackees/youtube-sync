"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync.youtube_sync import YouTubeSync

HERE = Path(__file__).parent
TEST_DATA = HERE / "test_data" / "test_sync"


class SyncTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        channel_name = "@silverguru"
        limit_scroll_pages = 1
        download_limit = 1
        media_output = TEST_DATA
        yt = YouTubeSync(channel_name=channel_name, media_output=media_output)
        yt.scan_for_vids(limit_scroll_pages=limit_scroll_pages)
        if len(yt.downloaded_vids()) < download_limit:
            yt.download(download_limit, yt_dlp_uses_docker=False)


if __name__ == "__main__":
    unittest.main()
