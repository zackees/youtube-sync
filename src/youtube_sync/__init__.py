from pathlib import Path

from .base_sync import BaseSync
from .create import create
from .library import VidEntry
from .types import Source


class YouTubeSync:
    def __init__(
        self,
        channel_name: str,
        media_output: Path,
        source: Source,
        library_path: Path | None = None,
        channel_url: str | None = None,
        yt_dlp_uses_docker: bool = False,
    ):
        self.source = source
        self.api: BaseSync = create(
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


__all__ = ["YouTubeSync"]
