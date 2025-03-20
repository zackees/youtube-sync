# pylint: disable=too-many-locals

"""
Scrapes the brighteon website for video urls and downloads them.
"""

import logging

from youtube_sync.library import VidEntry

# Set up module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.FATAL)


def scan_for_vids(
    channel_url: str,
    stored_vids: list[VidEntry],
    full_scan: bool,
    limit: int | None,
) -> list[VidEntry]:
    """Scan for videos on the channel."""
    from youtube_sync.brighteon.generic import scan_for_vids

    out: list[VidEntry] = scan_for_vids(
        channel_url=channel_url,
        stored_vids=stored_vids,
        full_scan=full_scan,
        limit=limit,
    )
    return out
