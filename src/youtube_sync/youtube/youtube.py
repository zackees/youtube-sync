"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.library import Library
from youtube_sync.types import VidEntry
from youtube_sync.youtube.bot import fetch_all_vids


def to_channel_url(channel: str) -> str:
    """Convert channel name to channel URL."""
    out = f"https://www.youtube.com/{channel}/videos"
    return out


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
    library: Library,
    limit_scroll_pages: int | None,  # None means no limit
    download: bool,
    download_limit: int | None,
    scan: bool,
    yt_dlp_uses_docker: bool = False,
) -> None:
    # library = youtube_library(Path(output))
    if scan:
        youtube_scan(library=library, limit_scroll_pages=limit_scroll_pages)

    if download:
        # lib.download_missing(download_limit)
        youtube_download_missing(
            library=library,
            download_limit=download_limit,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )
