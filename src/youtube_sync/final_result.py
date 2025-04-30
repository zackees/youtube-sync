from dataclasses import dataclass

from youtube_sync import FSPath


@dataclass
class FinalResult:
    url: str
    outmp3: FSPath
    exception: Exception | None
