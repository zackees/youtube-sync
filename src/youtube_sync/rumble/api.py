"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import Source, VidEntry


class RumbleSyncImpl(BaseSync):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        self.yt_dlp_uses_docker = yt_dlp_uses_docker
        self.lib: Library = library

    def library(self) -> Library:
        assert isinstance(self.lib, Library)
        return self.lib

    def source(self) -> Source:
        return Source.YOUTUBE

    def downloaded_vids(self, refresh: bool) -> list[VidEntry]:
        # return self.lib.downloaded_vids(load=refresh)
        raise NotImplementedError("RumbleSyncImpl.downloaded_vids")

    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        from youtube_sync.rumble.rumble_extra import rumble_scan

        rumble_scan(
            library=self.lib,
            limit_scroll_pages=limit_scroll_pages,
        )

    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None,
    ) -> None:
        self.scan_for_vids(limit_scroll_pages)
        self.download(download_limit, yt_dlp_uses_docker)
