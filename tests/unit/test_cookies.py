"""
Unit test file.
"""

import tempfile
import unittest
from pathlib import Path

from youtube_sync import Source
from youtube_sync.cookies import (
    Cookies,
    logger,
    set_cookie_refresh_seconds,
    set_cookie_root_path,
)
from youtube_sync.logutil import set_global_logging_level

set_global_logging_level("DEBUG")

logger.setLevel("DEBUG")


class CookiesTester(unittest.TestCase):
    """Main tester class."""

    def test_cookies(self) -> None:
        """Test command line interface (CLI)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            set_cookie_root_path(output_dir)
            cookies = Cookies.load(source=Source.YOUTUBE)
            print(f"Found {len(cookies)} cookies.")
            for cookie in cookies:
                print(cookie)
            pkl = output_dir / "youtube" / "cookies.pkl"
            txt = output_dir / "youtube" / "cookies.txt"
            self.assertTrue(pkl.exists(), f"{pkl} not found.")
            self.assertTrue(txt.exists(), f"{txt} not found.")

    def test_refresh_off(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            set_cookie_root_path(output_dir)
            cookies = Cookies.load(source=Source.YOUTUBE)
            print(f"Found {len(cookies)} cookies.")
            for cookie in cookies:
                print(cookie)
            pkl = output_dir / "youtube" / "cookies.pkl"
            txt = output_dir / "youtube" / "cookies.txt"
            self.assertTrue(pkl.exists(), f"{pkl} not found.")
            self.assertTrue(txt.exists(), f"{txt} not found.")
            creation_time = cookies.creation_time
            set_cookie_refresh_seconds(0)
            cookies.refresh()
            self.assertNotEqual(creation_time, cookies.creation_time)


if __name__ == "__main__":
    unittest.main()
