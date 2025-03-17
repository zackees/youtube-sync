# pylint: disable=too-many-arguments

"""Library json module."""

import json
from dataclasses import dataclass
from pathlib import Path

from youtube_sync.types import Source, VidEntry


@dataclass
class LibraryData:
    """Library data."""

    channel_name: str
    channel_url: str
    source: Source
    vids: list[VidEntry]

    def to_json(self) -> dict:
        """Convert to dictionary."""
        return {
            "channel_name": self.channel_name,
            "channel_url": self.channel_url,
            "source": self.source.value,
            "vids": [vid.to_dict() for vid in self.vids],
        }

    def to_json_str(self, minify=False) -> str:
        """Convert to json string."""
        data = self.to_json()
        indent = None if minify else 4
        return json.dumps(data, indent=indent)

    def merge(self, vids: list[VidEntry]) -> None:
        """Merge two libraries."""
        for vid in vids:
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
            channel_name = data["channel_name"]
            channel_url = data["channel_url"]
            source = Source.from_str(data["source"])
            vids = [VidEntry.from_dict(vid) for vid in data["vids"]]
            return LibraryData(
                channel_name=channel_name,
                channel_url=channel_url,
                source=source,
                vids=vids,
            )
        except FileNotFoundError as fe:
            return fe
        except Exception as e:
            return e

    def __repr__(self):
        return self.to_json_str()

    def __str__(self):
        return self.to_json_str()
