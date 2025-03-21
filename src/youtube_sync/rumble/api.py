"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import GenericSyncImpl
from youtube_sync.library import Library


class RumbleSyncImpl(GenericSyncImpl):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        super().__init__(library, yt_dlp_uses_docker)

    def to_channel_url(self, channel_name: str) -> str:
        from youtube_sync.rumble.rumble import to_channel_url

        return to_channel_url(channel_name)
