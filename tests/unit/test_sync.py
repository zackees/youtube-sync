"""
Unit test file.
"""

import unittest
from pathlib import Path

from youtube_sync import RealFS, Source, YouTubeSync

HERE = Path(__file__).parent
_TEST_DATA = HERE / "test_data" / "test_sync"
_TEST_DATA.mkdir(parents=True, exist_ok=True)
TEST_DATA = RealFS.from_path(_TEST_DATA)


class SyncTester(unittest.TestCase):
    """Main tester class."""

    # @unittest.skip("Silverguru channel is already filled")
    def test_simple(self) -> None:
        # shutil.rmtree(TEST_DATA, ignore_errors=True)
        try:
            channel_name = "silverguru"
            channel_id = "@silverguru"
            limit_scan = 1
            download_limit = 1
            media_output = TEST_DATA
            yt = YouTubeSync(
                channel_name=channel_name,
                channel_id=channel_id,
                media_output=media_output,
                source=Source.YOUTUBE,
            )
            yt.scan_for_vids(limit=limit_scan)
            all_downloaded = yt.find_vids_already_downloaded()
            if len(all_downloaded) < download_limit:
                yt.download(download_limit)
            total_downloaded = yt.find_vids_already_downloaded()
            print(f"Total downloaded: {len(total_downloaded)}")
            print(f"Total already downloaded: {len(all_downloaded)}")
            self.assertGreaterEqual(len(total_downloaded), download_limit)
            print("Done")
        finally:
            TEST_DATA.rmtree(ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
