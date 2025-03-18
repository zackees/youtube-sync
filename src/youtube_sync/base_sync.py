"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from abc import ABC, abstractmethod

from youtube_sync.library import Library
from youtube_sync.types import Source, VidEntry


class BaseSync(ABC):
    """Abstract base class defining the interface for YouTube synchronization."""

    def __init__(self, library: Library, yt_dlp_uses_docker: bool = False):
        self.yt_dlp_uses_docker = yt_dlp_uses_docker
        self.lib: Library = library

    def library(self) -> Library:
        """Return the library object."""
        return self.lib

    def download(
        self, download_limit: int | None, yt_dlp_uses_docker: bool | None
    ) -> None:
        """Download videos with optional limit and docker configuration."""
        yt_dlp_uses_docker = bool(yt_dlp_uses_docker)
        self.lib.download_missing(
            download_limit=download_limit, yt_dlp_uses_docker=yt_dlp_uses_docker
        )

    def source(self) -> Source:
        """Return the source object."""
        return self.lib.source

    @abstractmethod
    def scan_for_vids(self, limit_scroll_pages: int | None) -> list[VidEntry]:
        """Scan for videos with optional limit on scroll pages."""
        pass
