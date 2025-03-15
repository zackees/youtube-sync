# pylint: disable=too-many-arguments

"""Library json module."""

import os
import traceback
import warnings
from datetime import datetime
from pathlib import Path

from appdirs import user_data_dir
from filelock import SoftFileLock

from youtube_sync.downloadmp3 import download_mp3
from youtube_sync.vid_entry import VidEntry


def _get_library_json_lock_path() -> str:
    """Get the library json path."""
    return os.path.join(user_data_dir("youtube-sync"), "library.json.lock")


_FILE_LOCK = SoftFileLock(_get_library_json_lock_path())


def find_missing_downloads(library_json_path: Path) -> list[VidEntry]:
    """Find missing downloads."""
    pardir = os.path.dirname(library_json_path)
    out: list[VidEntry] = []
    data = load_json(library_json_path)
    for vid in data:
        file_path = vid.file_path
        if not os.path.exists(os.path.join(pardir, file_path)):
            # if error
            if not vid.error:
                out.append(vid)
            else:
                warnings.warn(f"Skipping {vid.url} because it is marked as an error.")
    all_have_a_date = all(vid.date for vid in out)
    if all_have_a_date:
        # sort oldest first
        out.sort(key=lambda vid: vid.date)  # type: ignore
    return out


def load_json(file_path: Path) -> list[VidEntry]:
    """Load json from file."""
    with _FILE_LOCK:
        data = file_path.read_text(encoding="utf-8")
    return VidEntry.deserialize(data)


def save_json(file_path: Path, data: list[VidEntry]) -> None:
    """Save json to file."""
    json_out = VidEntry.serialize(data)
    with _FILE_LOCK:
        file_path.write_text(json_out, encoding="utf-8")


def merge_into_library(library_json_path: Path, vids: list[VidEntry]) -> None:
    """Merge the vids into the library."""
    found_entries: list[VidEntry] = []
    for vid in vids:
        title = vid.title
        file_path = vid.file_path
        found_entries.append(
            VidEntry(url=vid.url, title=title, file_path=file_path, date=vid.date)
        )

    existing_entries = load_json(library_json_path)
    for found in found_entries:
        if found not in existing_entries:
            existing_entries.append(found)
    save_json(library_json_path, existing_entries)


class Library:
    """Represents the library"""

    def __init__(self, library_json_path: Path) -> None:
        self.library_json_path = library_json_path
        self.base_dir = library_json_path.parent
        if not library_json_path.exists():
            save_json(library_json_path, [])

    @property
    def path(self) -> Path:
        """Get the path."""
        return self.library_json_path

    def find_missing_downloads(self) -> list[VidEntry]:
        """Find missing downloads."""
        return find_missing_downloads(self.library_json_path)

    def load(self) -> list[VidEntry]:
        """Load json from file."""
        return load_json(self.library_json_path)

    def save(self, data: list[VidEntry]) -> None:
        """Save json to file."""
        save_json(self.library_json_path, data)

    def merge(self, vids: list[VidEntry]) -> None:
        """Merge the vids into the library."""
        merge_into_library(self.library_json_path, vids)

    def download_missing(self, download_limit: int = -1) -> None:
        """Download the missing files."""
        download_count = 0
        while True:
            if download_limit != -1 and download_count >= download_limit:
                break
            missing_downloads = self.find_missing_downloads()
            # make full paths
            if not missing_downloads:
                break
            vid = missing_downloads[0]
            next_url = vid.url
            next_mp3_path = os.path.join(self.base_dir, vid.file_path)
            print(
                f"\n#######################\n# Downloading missing file {next_url}: {next_mp3_path}\n"
                "###################"
            )
            try:
                download_mp3(url=next_url, outmp3=next_mp3_path)
            except Exception as e:  # pylint: disable=broad-except
                stacktrace_str = traceback.format_exc()
                print(f"Error downloading {next_url}: {e}")
                print(stacktrace_str)
                self.mark_error(vid)
            download_count += 1

    def mark_error(self, vid: VidEntry) -> None:
        """Mark the vid as an error."""
        vid.error = True
        self.merge([vid])
        print(f"Marked {vid.url} as an error.")

    def date_range(self) -> tuple[datetime, datetime] | None:
        """Get the date range."""
        vids = self.load()
        dates = [vid.date for vid in vids if vid.date]
        if not dates:
            return None
        return min(dates), max(dates)
