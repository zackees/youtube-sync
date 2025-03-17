"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import VidEntry
from youtube_sync.youtube.youtube import (
    youtube_download_missing,
    youtube_scan,
)


class YouTubeSyncImpl(BaseSync):
    def __init__(
        self,
        library: Library,
        yt_dlp_uses_docker: bool = False,
    ):
        self.yt_dlp_uses_docker = yt_dlp_uses_docker
        self.lib: Library = library

    def downloaded_vids(self, refresh) -> list[VidEntry]:
        return self.lib.downloaded_vids(load=refresh)

    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        youtube_scan(
            library=self.lib,
            limit_scroll_pages=limit_scroll_pages,
        )

    def library(self) -> Library:
        return self.lib

    def download(
        self, download_limit: int | None, yt_dlp_uses_docker: bool | None
    ) -> None:
        yt_dlp_uses_docker = (
            yt_dlp_uses_docker
            if yt_dlp_uses_docker is not None
            else self.yt_dlp_uses_docker
        )
        youtube_download_missing(
            library=self.lib,
            download_limit=download_limit,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None,
    ) -> None:
        self.scan_for_vids(limit_scroll_pages)
        self.download(download_limit, yt_dlp_uses_docker)
