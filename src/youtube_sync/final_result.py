from dataclasses import dataclass
from datetime import datetime

from youtube_sync.ytdlp.download_request import DownloadRequest


@dataclass
class FinalResult:
    request: DownloadRequest
    date: datetime | None
    exception: Exception | None
