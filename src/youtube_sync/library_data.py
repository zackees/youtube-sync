# pylint: disable=too-many-arguments

"""Library json module."""

import json
from dataclasses import dataclass

from youtube_sync import FSPath
from youtube_sync.types import Source
from youtube_sync.vid_entry import VidEntry


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
            for inner_vid in self.vids:
                if inner_vid.url == vid.url:
                    # Merge in the field.
                    inner_vid.date_upload = (
                        vid.date_upload if vid.date_upload else inner_vid.date_upload
                    )
                    break
            else:
                self.vids.append(vid)

    def __eq__(self, value) -> bool:
        if not isinstance(value, LibraryData):
            return False
        return self.vids == value.vids

    def __ne__(self, value) -> bool:
        return not self.__eq__(value)

    @staticmethod
    def from_json(data: dict | FSPath) -> "LibraryData | Exception | FileNotFoundError":
        """Create from dictionary."""
        try:
            if isinstance(data, FSPath):
                try:
                    data_str = data.read_text()
                    data = json.loads(data_str)
                    assert isinstance(data, dict)
                except FileNotFoundError as e:
                    return e
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
