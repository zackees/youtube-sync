"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

import os
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
    limit_scroll_pages: int,
    skip_scan: bool,
    yt_dlp_uses_docker: bool,
) -> Library:
    if yt_dlp_uses_docker:
        os.environ["USE_DOCKER_YT_DLP"] = "1"
    channel_url = library.channel_url
    # base_dir = Path(basedir)
    # output_dir = str(base_dir / channel / "youtube")
    if not skip_scan:
        vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
        library.merge(vids, save=True)
        print(f"Updated {library.path}")
    else:
        if not library.path.exists():
            raise FileNotFoundError(f"{library.path} does not exist. Cannot skip scan.")
    return library


def youtube_download_missing(library: Library, download_limit: int) -> Library:
    library.download_missing(download_limit)
    return library


def youtube_sync(
    channel_name: str,
    media_output: Path,
    limit_scroll_pages: int,
    download: bool,
    download_limit: int,
    skip_scan: bool,
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
    youtube_scan(
        library=lib,
        limit_scroll_pages=limit_scroll_pages,
        skip_scan=skip_scan,
        yt_dlp_uses_docker=yt_dlp_uses_docker,
    )

    if download:
        # lib.download_missing(download_limit)
        youtube_download_missing(lib, download_limit)

    return lib
