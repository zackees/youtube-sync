"""
Unit test file.
"""

import tempfile
import unittest
from pathlib import Path

from youtube_sync import Source
from youtube_sync.cookies import Cookies, set_cookie_root_path


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


if __name__ == "__main__":
    unittest.main()
