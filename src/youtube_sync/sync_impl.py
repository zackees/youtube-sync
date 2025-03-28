"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from abc import ABC, abstractmethod
from pathlib import Path

from youtube_sync.cookies import Cookies
from youtube_sync.library import Library
from youtube_sync.types import Source
from youtube_sync.vid_entry import VidEntry

_YOUTUBE_USE_BOT_SCANNER = False


class BaseSync(ABC):
    """Abstract base class defining the interface for YouTube synchronization."""

    def __init__(self, library: Library):
        self.lib: Library = library

    def library(self) -> Library:
        """Return the library object."""
        return self.lib

    def download(self, limit: int | None) -> None:
        """Download videos with optional limit."""
        self.lib.download_missing(
            limit=limit,
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


# A generic implementation of the BaseSync interface using yt-dlp
class YtDlpSync(BaseSync):
    def __init__(self, library: Library):
        super().__init__(library)
        self.cookies: Cookies | None = None

    @abstractmethod
    def channel_source(self) -> Source:
        pass

    def to_channel_url(self, channel_id: str) -> str:
        from youtube_sync.to_channel_url import to_channel_url

        source = self.channel_source()
        out = to_channel_url(source=source, channel_id=channel_id)
        return out

    def scan_for_vids(
        self,
        limit: int | None,
        stop_on_duplicate_vids: bool,
    ) -> list[VidEntry]:
        # get_cookies

        from youtube_sync.ytdlp.scan_for_vids import scan_for_vids

        self.cookies = Cookies.get_or_refresh(
            source=self.channel_source(), cookies=self.cookies
        )

        channel_name = self.lib.channel_name
        channel_url = self.to_channel_url(channel_name)
        if "http" not in channel_url:
            raise ValueError(f"Invalid channel URL: {channel_url}")
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
            cookies_txt=Path(self.cookies.path_txt),
        )

        return out


class RumbleSyncImpl(YtDlpSync):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.RUMBLE


class YouTubeSyncImpl(YtDlpSync):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.YOUTUBE

    def _bot_scan(self, limit: int | None) -> list[VidEntry]:
        from youtube_sync.youtube.scan import youtube_scan

        channel_url = self.to_channel_url(self.lib.channel_name)
        limit_scroll_pages = max(1, limit // 10) if limit is not None else None
        return youtube_scan(
            channel_url=channel_url,
            limit_scroll_pages=limit_scroll_pages,
        )

    # override
    def scan_for_vids(
        self,
        limit: int | None,
        stop_on_duplicate_vids: bool,
    ) -> list[VidEntry]:
        if _YOUTUBE_USE_BOT_SCANNER:
            return self._bot_scan(limit)
        else:
            return super().scan_for_vids(limit, stop_on_duplicate_vids)


class BrighteonSyncImpl(YtDlpSync):
    def __init__(self, library: Library):
        super().__init__(library)

    def channel_source(self) -> Source:
        return Source.BRIGHTEON
