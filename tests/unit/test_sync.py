"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync import Source, YouTubeSync
from youtube_sync.filesystem import RealFileSystem

HERE = Path(__file__).parent
_TEST_DATA = HERE / "test_data" / "test_sync"
TEST_DATA = RealFileSystem.get_real_path(_TEST_DATA)


class SyncTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        # shutil.rmtree(TEST_DATA, ignore_errors=True)
        TEST_DATA.rmtree(ignore_errors=True)
        channel_name = "@silverguru"
        limit_scan = 1
        download_limit = 1
        media_output = TEST_DATA
        yt = YouTubeSync(
            channel_name=channel_name,
            media_output=media_output,
            source=Source.YOUTUBE,
        )
        yt.scan_for_vids(limit=limit_scan)
        all_downloaded = yt.find_vids_already_downloaded()
        if len(all_downloaded) < download_limit:
            yt.download(download_limit)
        total_downloaded = yt.find_vids_already_downloaded()
        self.assertGreaterEqual(len(total_downloaded), download_limit)
        print("Done")


if __name__ == "__main__":
    unittest.main()
