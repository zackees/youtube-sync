# pylint: disable=too-many-arguments

"""Library json module."""

import json
from dataclasses import dataclass
from pathlib import Path

from youtube_sync.vid_entry import VidEntry


@dataclass
class LibraryData:
    """Library data."""

    vids: list[VidEntry]

    def to_json(self) -> dict:
        """Convert to dictionary."""
        return {"vids": [vid.to_dict() for vid in self.vids]}

    def to_json_str(self) -> str:
        """Convert to json string."""
        return json.dumps(self.to_json())

    def merge(self, other: "LibraryData") -> None:
        """Merge two libraries."""
        for vid in other.vids:
            if vid not in self.vids:
                self.vids.append(vid)

    def __eq__(self, value) -> bool:
        if not isinstance(value, LibraryData):
            return False
        return self.vids == value.vids

    def __ne__(self, value) -> bool:
        return not self.__eq__(value)

    @staticmethod
    def from_json(data: dict | Path) -> "LibraryData | Exception | FileNotFoundError":
        """Create from dictionary."""
        try:
            if isinstance(data, Path):
                data_str = data.read_text(encoding="utf-8")
                data = json.loads(data_str)
                assert isinstance(data, dict)
            vids = [VidEntry.from_dict(vid) for vid in data["vids"]]
            return LibraryData(vids)
        except FileNotFoundError as fe:
            return fe
        except Exception as e:
            return e

    def __repr__(self):
        return self.to_json_str()

    def __str__(self):
        return self.to_json_str()
