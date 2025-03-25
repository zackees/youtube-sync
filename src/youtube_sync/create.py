"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.library import Library
from youtube_sync.sync_impl import (
    BaseSync,
    BrighteonSyncImpl,
    RumbleSyncImpl,
    YouTubeSyncImpl,
)
from youtube_sync.types import Source


def create(
    source: Source,
    library: Library,
) -> BaseSync:

    out: BaseSync
    if source == Source.YOUTUBE:
        out = YouTubeSyncImpl(
            library=library,
        )
        return out
    if source == Source.RUMBLE:
        out = RumbleSyncImpl(
            library=library,
        )
        return out
    if source == Source.BRIGHTEON:
        out = BrighteonSyncImpl(
            library=library,
        )
        return out
    raise ValueError(f"Unknown source: {source}")
