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


def youtube_library(outputh_path: Path) -> Library:
    # library_json = os.path.join(output_name, "library.json")
    library_json = outputh_path / "library.json"
    library = Library(library_json)
    return library


def youtube_scan(
    channel_name: str,
    output: str,
    limit_scroll_pages: int,
    skip_scan: bool,
    yt_dlp_uses_docker: bool,
) -> Library:
    if yt_dlp_uses_docker:
        os.environ["USE_DOCKER_YT_DLP"] = "1"
    channel_url = to_channel_url(channel_name)
    # base_dir = Path(basedir)
    # output_dir = str(base_dir / channel / "youtube")
    output_dir = output
    limit_scroll_pages = limit_scroll_pages
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    library_json = Path(output_dir) / "library.json"
    library = Library(library_json)
    if not skip_scan:
        vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
        library.merge(vids)
        print(f"Updated {library_json}")
    else:
        if not os.path.exists(library_json):
            raise FileNotFoundError(f"{library_json} does not exist. Cannot skip scan.")
    return library


def youtube_sync(
    channel_name: str,
    output: str,
    limit_scroll_pages: int,
    download: bool,
    download_limit: int,
    skip_scan: bool,
    yt_dlp_uses_docker: bool,
) -> Library:
    library = youtube_scan(
        channel_name=channel_name,
        output=output,
        limit_scroll_pages=limit_scroll_pages,
        skip_scan=skip_scan,
        yt_dlp_uses_docker=yt_dlp_uses_docker,
    )

    if download:
        library.download_missing(download_limit)

    return library
