"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from abc import ABC, abstractmethod

from youtube_sync.library import Library
from youtube_sync.types import Source, VidEntry


class BaseSync(ABC):
    """Abstract base class defining the interface for YouTube synchronization."""

    def __init__(self, library: Library):
        self.lib: Library = library

    def library(self) -> Library:
        """Return the library object."""
        return self.lib

    def download(self, download_limit: int | None) -> None:
        """Download videos with optional limit."""
        self.lib.download_missing(
            download_limit=download_limit,
        )

    def source(self) -> Source:
        """Return the source object."""
        return self.lib.source

    @abstractmethod
    def scan_for_vids(
        self, limit: int | None, stop_on_duplicate_vids: bool
    ) -> list[VidEntry]:
        """Scan for videos with optional limit on scroll pages."""
        pass


# BaseSync implementation that only needs the channel url conversion function.
class GenericSyncImpl(BaseSync):
    def __init__(self, library: Library):
        super().__init__(library)

    @abstractmethod
    def channel_source(self) -> Source:
        pass

    def to_channel_url(self, channel_name: str) -> str:
        from youtube_sync.to_channel_url import to_channel_url

        source = self.channel_source()
        out = to_channel_url(source=source, channel_name=channel_name)
        return out

    def scan_for_vids(
        self, limit: int | None, stop_on_duplicate_vids: bool
    ) -> list[VidEntry]:
        from youtube_sync.ytdlp_scan_for_vids import scan_for_vids

        channel_name = self.lib.channel_name
        channel_url = self.to_channel_url(channel_name)
        if stop_on_duplicate_vids:
            stored_vids = self.lib.load()
        else:
            stored_vids = []
        full_scan = limit is None
        limit = limit if limit is not None else -1
        out: list[VidEntry] = scan_for_vids(
            channel_url=channel_url,
            limit=limit,
            stored_vids=stored_vids,
            full_scan=full_scan,
        )
        return out


class RumbleSyncImpl(GenericSyncImpl):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.RUMBLE


class YouTubeSyncImpl(GenericSyncImpl):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.YOUTUBE


class BrighteonSyncImpl(GenericSyncImpl):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.BRIGHTEON
