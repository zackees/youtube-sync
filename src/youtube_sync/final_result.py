from dataclasses import dataclass
from datetime import datetime

from youtube_sync import FSPath


@dataclass
class FinalResult:
    url: str
    outmp3: FSPath
    date: datetime | None
    exception: Exception | None
