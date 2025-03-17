"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from pathlib import Path

from youtube_sync.base_sync import BaseSync
from youtube_sync.library import VidEntry
from youtube_sync.types import Source
from youtube_sync.youtube.api import (
    YouTubeSyncImpl,
)


def _make_api_object(
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


class YouTubeSync(BaseSync):
    def __init__(
        self,
        channel_name: str,
        media_output: Path,
        source: Source = Source.YOUTUBE,
        library_path: Path | None = None,
        channel_url: str | None = None,
        yt_dlp_uses_docker: bool = False,
    ):
        self.source = source
        self.api = _make_api_object(
            source=source,
            channel_name=channel_name,
            media_output=media_output,
            library_path=library_path,
            channel_url=channel_url,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    def downloaded_vids(self, refresh=True) -> list[VidEntry]:
        return self.api.downloaded_vids(refresh=refresh)

    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        self.api.scan_for_vids(limit_scroll_pages)

    def download(
        self, download_limit: int | None, yt_dlp_uses_docker: bool | None = None
    ) -> None:
        self.api.download(
            download_limit=download_limit, yt_dlp_uses_docker=yt_dlp_uses_docker
        )

    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None = None,
    ) -> None:
        self.api.sync(
            limit_scroll_pages=limit_scroll_pages,
            download_limit=download_limit,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
