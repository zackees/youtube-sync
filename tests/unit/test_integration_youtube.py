"""
Command entry point.
"""

import json
import os
import shutil
import unittest
from pathlib import Path

from youtube_sync import Source
from youtube_sync.integration_test import Args, integration_test

os.environ["FIX_MISSING_DATES"] = "0"

HERE = Path(__file__).parent

os.chdir(HERE.parent.parent)

PROJECT_ROOT = Path(".")
TMP_DST_DOWNLOAD = PROJECT_ROOT / "tmp" / "silverguru"

YOURTUBE_SILVER_GURU = Args(
    source=Source.YOUTUBE,
    channel_name="silverguru",
    channel_id="@silverguru",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)


def find_files(start_dir: Path) -> list[Path]:
    """Find all files in a directory and its subdirectories."""
    files = []
    for root, _, filenames in os.walk(start_dir):
        for filename in filenames:
            filepath = Path(root) / filename
            if filepath.is_file():
                files.append(filepath)
    return files


def _starts_with_date(filename: str) -> bool:
    """Check if the filename starts with a date."""
    parts = filename.split(" ")
    if len(parts) < 2:
        return False
    p1 = parts[0]

    if not len(p1) == 10:
        return False
    # try to parse YYYY-MM-DD
    try:
        _ = int(p1[0:4])
        _ = int(p1[5:7])
        _ = int(p1[8:10])
        return True
    except ValueError:
        return False


class YoutubeIntegrationTester(unittest.TestCase):
    """Main tester class."""

    # @unittest.skip("Test is failing right now")
    def test_imports(self) -> None:
        """Test command line interface (CLI)."""

        shutil.rmtree(TMP_DST_DOWNLOAD, ignore_errors=True)
        integration_test(YOURTUBE_SILVER_GURU)

        all_files = find_files(TMP_DST_DOWNLOAD)
        print(all_files)
        print("done")

        library_json = TMP_DST_DOWNLOAD / "youtube" / "library.json"
        self.assertTrue(library_json.is_file(), "Library JSON file not found.")

        text = library_json.read_text()
        json_data = json.loads(text)
        vids = json_data["vids"]
        self.assertIsNotNone(vids)
        first = vids[0]
        self.assertIsNotNone(first)
        file_path = first.get("file_path")
        self.assertIsNotNone(file_path)

        starts_with_date = _starts_with_date(file_path)
        self.assertTrue(starts_with_date, "File path does not start with date.")

        # now test that the file name starts with a date
        all_files = find_files(TMP_DST_DOWNLOAD)
        valid_mp3_files = [
            f
            for f in all_files
            if f.name.endswith(".mp3") and _starts_with_date(f.name)
        ]
        self.assertTrue(
            len(valid_mp3_files) == 1,
            f"Expectd exactly 1 mp3 file in correct format, found {len(valid_mp3_files)}",
        )
        print("done ")


if __name__ == "__main__":
    unittest.main()
