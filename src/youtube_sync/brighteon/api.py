"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from youtube_sync.base_sync import GenericSyncImpl, Source
from youtube_sync.library import Library


class BrighteonSyncImpl(GenericSyncImpl):
    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        super().__init__(library, yt_dlp_uses_docker)

    def channel_source(self) -> Source:
        return Source.BRIGHTEON
