"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import Source


def create(
    source: Source,
    library: Library,
    yt_dlp_uses_docker: bool = False,
) -> BaseSync:
    from youtube_sync.brighteon.api import BrighteonSyncImpl
    from youtube_sync.rumble.api import RumbleSyncImpl
    from youtube_sync.youtube.api import YouTubeSyncImpl

    out: BaseSync
    if source == Source.YOUTUBE:
        out = YouTubeSyncImpl(
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
        return out
    if source == Source.RUMBLE:
        out = RumbleSyncImpl(
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
        return out
    if source == Source.BRIGHTEON:
        out = BrighteonSyncImpl(
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
        return out
    raise ValueError(f"Unknown source: {source}")
