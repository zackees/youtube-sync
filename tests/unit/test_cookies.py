"""
Unit test file.
"""

import tempfile
import unittest
from pathlib import Path

from youtube_sync import Source
from youtube_sync.cookies import Cookies


class CookiesTester(unittest.TestCase):
    """Main tester class."""

    def test_cookies(self) -> None:
        """Test command line interface (CLI)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            cookies = Cookies.from_browser(source=Source.YOUTUBE)
            print(f"Found {len(cookies)} cookies.")
            for cookie in cookies:
                print(cookie)
            cookies.save(output_dir / "cookies.pkl")
            cookies.save(output_dir / "cookies.txt")
            self.assertTrue((output_dir / "cookies.pkl").exists())
            self.assertTrue((output_dir / "cookies.txt").exists())


if __name__ == "__main__":
    unittest.main()
