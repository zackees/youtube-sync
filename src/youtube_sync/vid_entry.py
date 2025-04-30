import json
from datetime import datetime
from pathlib import Path
from typing import Any

from youtube_sync.clean_filename import clean_filename

_DBG_ENABLE_VID_DUMP = False


def _dbg_vid_dump(data: dict | None) -> None:
    if not _DBG_ENABLE_VID_DUMP:
        return
    assert data is not None

    dbg_out_file = Path("sample.json")
    dbg_out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


class VidEntry:
    """Minimal information of a video on a channel."""

    def __init__(
        self,
        url: str,
        title: str,
        file_path: str | None = None,
        date: datetime | None = None,
        upload_date: datetime | None = None,
        error=False,
        data: dict | None = None,
    ) -> None:
        _dbg_vid_dump(data)
        assert "http" in url
        self.url = url
        self.title = title
        self.date = date
        self.data = data
        if file_path is None:
            self.file_path = clean_filename(f"{title}.mp3")
        else:
            self.file_path = clean_filename(file_path)
        if date is None:
            self.date = datetime.now()
        self.date_upload: datetime | None = upload_date
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
        dateupload_str: str | None = None
        if self.date_upload is not None:
            dateupload_str = self.date_upload.isoformat()
        return {
            "url": self.url,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "date_upload": dateupload_str,
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
        date: datetime | None = None
        if data is not None:
            json_date = data.get("date")
            if json_date is not None:
                date = datetime.fromisoformat(json_date)
        upload_date: datetime | None = None
        if data.get("date_upload") is not None:
            upload_date = datetime.fromisoformat(data["date_upload"])
        error = data.get("error", False)
        return VidEntry(
            url=data["url"],
            title=data["title"],
            date=date,
            upload_date=upload_date,
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
