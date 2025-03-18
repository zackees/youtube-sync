"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library


class RumbleSyncImpl(BaseSync):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        self.yt_dlp_uses_docker = yt_dlp_uses_docker
        self.lib: Library = library

    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        from youtube_sync.rumble.rumble_extra import rumble_scan

        rumble_scan(
            library=self.lib,
            limit_scroll_pages=limit_scroll_pages,
        )
