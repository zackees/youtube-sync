"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import BaseSync
from youtube_sync.library import Library
from youtube_sync.types import VidEntry


class BrighteonSyncImpl(BaseSync):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        super().__init__(library, yt_dlp_uses_docker)

    def scan_for_vids(self, limit_scroll_pages: int) -> list[VidEntry]:
        from youtube_sync.brighteon.bot import scan_for_vids

        channel_name = self.lib.channel_name
        channel_url = f"https://www.brighteon.com/channels/{channel_name}"
        stored_vids = self.lib.load()
        full_scan = limit_scroll_pages is None
        out: list[VidEntry] = scan_for_vids(
            channel_url=channel_url,
            limit=limit_scroll_pages,
            stored_vids=stored_vids,
            full_scan=full_scan,
        )
        return out
