import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from youtube_sync.clean_filename import clean_filename


class VideoId(str):
    pass


class ChannelId(str):
    pass


class ChannelName(str):
    pass


class ChannelUrl(str):
    pass


class Source(Enum):
    """Source enum."""

    YOUTUBE = "youtube"
    RUMBLE = "rumble"
    BRIGHTEON = "brighteon"

    @staticmethod
    def from_str(value: str) -> "Source":
        """Convert from string."""
        value = value.lower()
        if value == "youtube":
            return Source.YOUTUBE
        if value == "rumble":
            return Source.RUMBLE
        if value == "brighteon":
            return Source.BRIGHTEON
        raise ValueError(f"Unknown source: {value}")

    @staticmethod
    def check(value: "str | Source") -> bool:
        """Check if value is a Source."""
        if isinstance(value, Source):
            return True
        try:
            _ = Source.from_str(value)
            return True
        except ValueError:
            return False


@dataclass
class VidEntry:
    """Minimal information of a video on a channel."""

    url: str
    title: str
    file_path: str
    date: datetime | None
    error: bool = False

    def __init__(
        self,
        url: str,
        title: str,
        file_path: str | None = None,
        date: datetime | None = None,
        error=False,
    ) -> None:
        self.url = url
        self.title = title
        self.date = date
        if file_path is None:
            self.file_path = clean_filename(f"{title}.mp3")
        else:
            self.file_path = clean_filename(file_path)
        self.error = error

    # needed for set membership
    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other: Any):
        if not isinstance(other, VidEntry):
            return False
        return self.url == other.url

    def __repr__(self) -> str:
        data = self.to_dict()
        return json.dumps(data)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "file_path": self.file_path,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VidEntry":
        """Create from dictionary."""
        filepath = data.get("file_path")
        if filepath is None:
            filepath = clean_filename(data["title"])
        filepath = clean_filename(filepath)
        date = datetime.fromisoformat(data["date"]) if data.get("date") else None
        error = data.get("error", False)
        return VidEntry(
            url=data["url"],
            title=data["title"],
            date=date,
            file_path=filepath,
            error=error,
        )

    @classmethod
    def serialize(cls, data: list["VidEntry"]) -> str:
        """Serialize to string."""
        json_data = [vid.to_dict() for vid in data]
        return json.dumps(json_data, indent=2)

    @classmethod
    def deserialize(cls, data: str) -> list["VidEntry"]:
        """Deserialize from string."""
        # return [cls.from_dict(vid) for vid in json.loads(data)]
        out: list[VidEntry] = []
        try:
            for vid in json.loads(data):
                try:
                    out.append(cls.from_dict(vid))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:  # pylint: disable=broad-except
                    print(f"Failed to deserialize {vid}: {e}")
        except Exception as e:  # pylint: disable=broad-except
            print(f"Failed to deserialize {data}: {e}")
        return out
