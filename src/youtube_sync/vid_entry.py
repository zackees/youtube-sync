import json
from datetime import date, datetime
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


def _parse_date_from_str(date_str: str | None) -> date | None:
    """dates will like 2023-10-01T12:00:00Z or 2023-10-01"""
    if date_str is None:
        return None
    # First try normal datetime format
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.date()
    except ValueError:
        # if that fails then attempt to do a straight YYYY-MM-DD parse
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.date()
        except ValueError:
            # if that fails then return None
            raise


class VidEntry:
    """Minimal information of a video on a channel."""

    def __init__(
        self,
        url: str,
        title: str,
        file_path: str | None = None,
        creation_date: datetime | None = None,
        upload_date: date | str | None = None,
        error=False,
        data: dict | None = None,
    ) -> None:
        assert isinstance(
            creation_date, datetime | None
        ), f"creation_date: {creation_date} is of type {type(creation_date)}"
        _dbg_vid_dump(data)
        assert "http" in url
        if isinstance(upload_date, str):
            upload_date = _parse_date_from_str(upload_date)
        self.url = url
        self.title = title
        self.date = creation_date
        upload_date_str = f"{upload_date} " if isinstance(upload_date, str) else ""
        if file_path is None:
            self.file_path = clean_filename(f"{upload_date_str}{title}.mp3")
        else:
            self.file_path = file_path
        if creation_date is None:
            self.date = datetime.now()
        self.date_upload: date | None = upload_date
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
        creation_date: datetime | None = None
        if data is not None:
            json_date = data.get("date")
            if json_date is not None:
                creation_date = datetime.fromisoformat(json_date)
        upload_date: date | None = None
        if data.get("date_upload") is not None:
            upload_date_str = data["date_upload"]
            # upload_date = date.fromisoformat(upload_date_str)
            upload_date = _parse_date_from_str(upload_date_str)
        error = data.get("error", False)
        return VidEntry(
            url=data["url"],
            title=data["title"],
            creation_date=creation_date,
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
