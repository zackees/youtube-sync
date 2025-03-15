"""
Unit test file.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from youtube_sync.library import Library


class LibraryTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        """Test command line interface (CLI)."""
        with TemporaryDirectory() as temp_dir:
            libjson = Path(temp_dir) / "library.json"
            lib: Library = Library(libjson)
            print(lib.path)
            print("done")


if __name__ == "__main__":
    unittest.main()
