"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from pathlib import Path

from youtube_sync.vid_entry import VidEntry
from youtube_sync.youtube.bot_scanner import scan_vids


def youtube_scan(
    channel_url: str,
    limit_scroll_pages: int | None,
) -> list[VidEntry]:
    # base_dir = Path(basedir)
    # output_dir = str(base_dir / channel / "youtube")
    vids: list[VidEntry] = scan_vids(channel_url, limit=limit_scroll_pages)
    return vids


# Interface for engine
def scan_for_vids(
    channel_url: str,
    stored_vids: list[VidEntry],
    limit: int | None,
    cookies_txt: Path | None,
    full_scan: bool | None = None,
) -> list[VidEntry]:
    return youtube_scan(channel_url, limit)
