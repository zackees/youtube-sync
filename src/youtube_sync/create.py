"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import Source
from youtube_sync.youtube.api import (
    YouTubeSyncImpl,
)


def create(
    source: Source,
    library: Library,
    yt_dlp_uses_docker: bool = False,
) -> BaseSync:
    if source == Source.YOUTUBE:
        out = YouTubeSyncImpl(
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
        return out
    raise ValueError(f"Unknown source: {source}")
