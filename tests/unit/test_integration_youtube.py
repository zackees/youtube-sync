"""
Command entry point.
"""

import unittest

from youtube_sync import Source
from youtube_sync.integration_test import Args, integration_test

YOURTUBE_SILVER_GURU = Args(
    source=Source.YOUTUBE,
    channel_name="silverguru",
    channel_id="@silverguru",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)


class YoutubeIntegrationTester(unittest.TestCase):
    """Main tester class."""

    # @unittest.skip("Test is failing right now")
    def test_imports(self) -> None:
        """Test command line interface (CLI)."""
        integration_test(YOURTUBE_SILVER_GURU)


if __name__ == "__main__":
    unittest.main()
