"""
Unit test file.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from youtube_sync.library import Library
from youtube_sync.vid_entry import VidEntry


class LibraryTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        """Test command line interface (CLI)."""
        with TemporaryDirectory() as temp_dir:
            libjson = Path(temp_dir) / "library.json"
            lib: Library = Library(libjson)
            print(lib.path)
            ve: VidEntry = VidEntry(
                "https://www.youtube.com/watch?v=123",
                "Some title",
                "some_title.mp3",
            )
            lib.merge([ve], save=True)
            lib2 = Library(libjson)
            print(lib2)
            print("done")


if __name__ == "__main__":
    unittest.main()
