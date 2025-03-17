from pathlib import Path

from .base_sync import BaseSync
from .create import create
from .library import Library
from .types import Source, VidEntry
from .youtube.youtube import to_channel_url as to_channel_url_youtube


def to_channel_url(source: Source, channel_name: str) -> str:
    if source == Source.YOUTUBE:
        return to_channel_url_youtube(channel_name)
    raise ValueError(f"Unknown source: {source}")


def make_library(
    channel_name: str,
    channel_url: str | None,  # None means auto-find
    media_output: Path,
    source: Source,
    library_path: (
        Path | None
    ) = None,  # None means place the library in the media_output
) -> Library:
    url = channel_url or to_channel_url(source=source, channel_name=channel_name)
    library_json = library_path or media_output / "library.json"
    library = Library(
        channel_name=channel_name,
        channel_url=url,
        source=source,
        json_path=library_json,
    )
    library.load()
    return library


class YouTubeSync:
    def __init__(
        self,
        channel_name: str,
        media_output: Path,
        source: Source,
        library_path: Path | None = None,
        channel_url: str | None = None,
        yt_dlp_uses_docker: bool = False,
    ) -> None:
        library = make_library(
            channel_name=channel_name,
            channel_url=channel_url,
            media_output=media_output,
            source=source,
            library_path=library_path,
        )

        self.api: BaseSync = create(
            source=source,
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    @property
    def library(self) -> Library:
        return self.api.library()

    @property
    def source(self) -> Source:
        return self.api.source()

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
