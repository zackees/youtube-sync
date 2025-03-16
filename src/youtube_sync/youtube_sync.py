"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from pathlib import Path

from youtube_sync.library import Library, VidEntry
from youtube_sync.youtube_bot import fetch_all_vids


def to_channel_url(channel: str) -> str:
    """Convert channel name to channel URL."""
    out = f"https://www.youtube.com/{channel}/videos"
    return out


def youtube_library(
    channel_name: str,
    channel_url: str | None,  # None means auto-find
    media_output: Path,
    library_path: (
        Path | None
    ) = None,  # None means place the library in the media_output
) -> Library:
    url = channel_url or to_channel_url(channel_name)
    library_json = library_path or media_output / "library.json"
    library = Library(
        channel_name=channel_name,
        channel_url=url,
        source="youtube",
        json_path=library_json,
    )
    library.load()
    return library


def youtube_scan(
    library: Library,
    limit_scroll_pages: int | None,
) -> Library:
    channel_url = library.channel_url
    # base_dir = Path(basedir)
    # output_dir = str(base_dir / channel / "youtube")
    vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
    library.merge(vids, save=True)
    print(f"Updated {library.path}")
    return library


def youtube_download_missing(
    library: Library, download_limit: int | None, yt_dlp_uses_docker: bool
) -> None:
    library.download_missing(
        download_limit=download_limit, yt_dlp_uses_docker=yt_dlp_uses_docker
    )


def youtube_sync(
    channel_name: str,
    media_output: Path,
    limit_scroll_pages: int | None,  # None means no limit
    download: bool,
    download_limit: int | None,
    scan: bool,
    library_path: (
        Path | None
    ) = None,  # None means place the library.json file in the media_output
    channel_url: str | None = None,  # None means auto-find
    yt_dlp_uses_docker: bool = False,
) -> Library:
    # library = youtube_library(Path(output))
    lib = youtube_library(
        channel_name=channel_name,
        channel_url=channel_url,
        media_output=media_output,
        library_path=library_path,
    )
    if scan:
        youtube_scan(library=lib, limit_scroll_pages=limit_scroll_pages)

    if download:
        # lib.download_missing(download_limit)
        youtube_download_missing(
            library=lib,
            download_limit=download_limit,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    return lib


class YouTubeSync:
    def __init__(
        self,
        channel_name: str,
        media_output: Path,
        library_path: Path | None = None,
        channel_url: str | None = None,
    ):
        self.lib: Library = youtube_library(
            channel_name=channel_name,
            channel_url=channel_url,
            media_output=media_output,
            library_path=library_path,
        )

    def downloaded_vids(self, refresh=True) -> list[VidEntry]:
        return self.lib.downloaded_vids(load=refresh)

    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        youtube_scan(
            library=self.lib,
            limit_scroll_pages=limit_scroll_pages,
        )

    def download(
        self,
        download_limit: int | None,
        yt_dlp_uses_docker: bool,
    ) -> None:
        youtube_download_missing(
            library=self.lib,
            download_limit=download_limit,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool,
    ) -> None:
        self.scan_for_vids(limit_scroll_pages)
        self.download(download_limit, yt_dlp_uses_docker)
