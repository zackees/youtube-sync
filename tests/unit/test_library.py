"""
Unit test file.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from youtube_sync import RealFS
from youtube_sync.library import Library
from youtube_sync.vid_entry import VidEntry


class LibraryTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        """Test command line interface (CLI)."""
        with TemporaryDirectory() as temp_dir:
            _json_path = Path(temp_dir) / "library.json"
            json_path = RealFS.from_path(_json_path)
            lib: Library = Library(
                channel_name="Some channel",
                channel_url="https://www.youtube.com/channel/123",
                source="youtube",
                json_path=json_path,
            )
            print(lib.path)
            ve: VidEntry = VidEntry(
                "https://www.youtube.com/watch?v=123",
                "Some title",
                "some_title.mp3",
            )
            lib.merge([ve], save=True)
            lib2 = Library.from_json(json_path)
            print(lib2)
            self.assertEqual(lib, lib2)
            print("done")


if __name__ == "__main__":
    unittest.main()
