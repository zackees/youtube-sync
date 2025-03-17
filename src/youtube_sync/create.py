"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from pathlib import Path

from youtube_sync.base_sync import BaseSync
from youtube_sync.types import Source
from youtube_sync.youtube.api import (
    YouTubeSyncImpl,
)


def create(
    source: Source,
    channel_name: str,
    media_output: Path,
    library_path: Path | None = None,
    channel_url: str | None = None,
    yt_dlp_uses_docker: bool = False,
) -> BaseSync:
    if source == Source.YOUTUBE:
        out = YouTubeSyncImpl(
            channel_name=channel_name,
            media_output=media_output,
            library_path=library_path,
            channel_url=channel_url,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
        return out
    raise ValueError(f"Unknown source: {source}")
