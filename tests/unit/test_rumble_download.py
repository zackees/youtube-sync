"""
Unit test for Rumble video download via yt-dlp.
Tests the streaming output and UTF-8 encoding fixes.
"""

import tempfile
import unittest
from pathlib import Path

from virtual_fs import RealFS

from youtube_sync.config import Source
from youtube_sync.final_result import DownloadRequest
from youtube_sync.ytdlp.downloader import YtDlpDownloader

# Rumble video URL to test
RUMBLE_VIDEO_URL = (
    "https://rumble.com/v6szu2f-spaceshot76-intro-mr-swickly.html"
    "?e9s=src_v1_s%2Csrc_v1_s_o&sci=1d09f114-33e1-4549-9692-3af711994629"
)


class RumbleDownloadTester(unittest.TestCase):
    """Test Rumble video download."""

    def test_rumble_download(self) -> None:
        """Test downloading a single Rumble video using yt-dlp internals."""
        print(f"\n{'='*60}")
        print(f"Testing Rumble download: {RUMBLE_VIDEO_URL}")
        print(f"{'='*60}\n")

        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_file = temp_path / "test_rumble_video.mp3"

            # Create filesystem path
            fs = RealFS()
            output_fspath = fs.get_path(output_file.as_posix())

            # Create download request
            download_request = DownloadRequest(
                url=RUMBLE_VIDEO_URL,
                outmp3=output_fspath,
                download_vid=True,  # Download the video
                download_date=True,  # Get upload date
            )

            # Create downloader instance
            downloader = YtDlpDownloader(
                di=download_request,
                source=Source.RUMBLE,
                cookies_txt=None,  # No cookies needed for Rumble
            )

            try:
                # Execute download
                print("Starting download...")
                download_result = downloader.download()

                # Check if download was successful
                if isinstance(download_result, Exception):
                    self.fail(f"Download failed with error: {download_result}")

                print("\nDownload completed successfully!")
                print(f"Upload date: {download_result.upload_date}")
                print(f"Downloaded file: {download_result.downloaded_mp3}")

                # Verify we got the upload date
                self.assertIsNotNone(
                    download_result.upload_date,
                    "Upload date should be extracted",
                )

                # Verify the file was downloaded
                self.assertIsNotNone(
                    download_result.downloaded_mp3,
                    "Downloaded file should exist",
                )

                # Convert to MP3
                print("\nConverting to MP3...")
                mp3_result = downloader.convert_to_mp3()

                if isinstance(mp3_result, Exception):
                    self.fail(f"MP3 conversion failed: {mp3_result}")

                print("Conversion successful!")

                # Copy to destination
                print(f"Copying to destination: {output_file}")
                downloader.copy_to_destination()

                # Verify output file exists
                self.assertTrue(
                    output_fspath.exists(),
                    f"Output file should exist at {output_file}",
                )

                # Check file size using Path object
                file_size = output_file.stat().st_size
                print(f"\nFinal MP3 file size: {file_size:,} bytes")
                self.assertGreater(
                    file_size,
                    1024,  # At least 1KB
                    "MP3 file should have content",
                )

                print(f"\n{'='*60}")
                print("Test PASSED: Rumble download successful!")
                print(f"{'='*60}\n")

            finally:
                # Cleanup
                downloader.dispose()


if __name__ == "__main__":
    unittest.main()
