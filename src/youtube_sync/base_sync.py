"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from abc import ABC, abstractmethod

from youtube_sync.library import Library
from youtube_sync.types import VidEntry


class BaseSync(ABC):
    """Abstract base class defining the interface for YouTube synchronization."""

    @abstractmethod
    def downloaded_vids(self, refresh) -> list[VidEntry]:
        """Return list of downloaded videos, optionally refreshing from disk."""
        pass

    @abstractmethod
    def scan_for_vids(self, limit_scroll_pages: int) -> None:
        """Scan for videos with optional limit on scroll pages."""
        pass

    @abstractmethod
    def download(
        self, download_limit: int | None, yt_dlp_uses_docker: bool | None
    ) -> None:
        """Download videos with optional limit and docker configuration."""
        pass

    @abstractmethod
    def library(self) -> Library:
        """Return the library object."""
        pass

    @abstractmethod
    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None,
    ) -> None:
        """Scan and download videos in one operation."""
        pass
