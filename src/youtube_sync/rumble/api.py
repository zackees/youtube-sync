"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import VidEntry


class RumbleSyncImpl(BaseSync):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        super().__init__(library, yt_dlp_uses_docker)

    def scan_for_vids(self, limit_scroll_pages: int | None) -> list[VidEntry]:
        from youtube_sync.rumble.rumble_extra import rumble_scan

        out: list[VidEntry] = rumble_scan(
            channel_name=self.lib.channel_name,
            limit_scroll_pages=limit_scroll_pages,
        )
        return out
