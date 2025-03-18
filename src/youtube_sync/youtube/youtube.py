"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.types import VidEntry
from youtube_sync.youtube.bot import fetch_all_vids


def to_channel_url(channel: str) -> str:
    """Convert channel name to channel URL."""
    out = f"https://www.youtube.com/{channel}/videos"
    return out


def youtube_scan(
    channel_url: str,
    limit_scroll_pages: int | None,
) -> list[VidEntry]:
    # base_dir = Path(basedir)
    # output_dir = str(base_dir / channel / "youtube")
    vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
    return vids
