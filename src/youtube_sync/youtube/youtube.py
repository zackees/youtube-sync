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
