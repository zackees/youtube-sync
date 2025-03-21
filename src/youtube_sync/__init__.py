from pathlib import Path

from .base_sync import BaseSync
from .create import create
from .downloadmp3 import update_yt_dlp
from .library import Library
from .types import Source, VidEntry


class YouTubeSync:
    def __init__(
        self,
        channel_name: str,
        media_output: Path,
        source: Source = Source.YOUTUBE,
        library_path: Path | None = None,
        channel_url: str | None = None,
        yt_dlp_uses_docker: bool = False,
    ) -> None:
        library = Library.get_or_create(
            channel_name=channel_name,
            channel_url=channel_url,
            media_output=media_output,
            source=source,
            library_path=library_path,
        )

        self.api: BaseSync = create(
            source=source,
            library=library,
            yt_dlp_uses_docker=yt_dlp_uses_docker,
        )

    @property
    def library(self) -> Library:
        return self.api.library()

    @property
    def source(self) -> Source:
        return self.api.source()

    def find_vids_missing_downloads(self, refresh=True) -> list[VidEntry]:
        if refresh:
            self.library.load()
        out = self.library.find_missing_downloads()
        return out

    def known_vids(self, refresh=True) -> list[VidEntry]:
        out = self.library.known_vids(load=refresh)
        return out

    def scan_for_vids(
        self, limit_scroll_pages: int | None, stop_on_duplicate_vids=False
    ) -> list[VidEntry]:
        out: list[VidEntry] = self.api.scan_for_vids(
            limit_scroll_pages, stop_on_duplicate_vids
        )
        self.library.merge(out, save=True)
        return out

    def find_vids_already_downloaded(self, refresh=True) -> list[VidEntry]:
        known_vids = self.known_vids(refresh=refresh)
        find_vids_missing_downloads = self.find_vids_missing_downloads()
        # all_downloaded = list(set(find_vids_missing_downloads) - set(known_vids))
        out: list[VidEntry] = []
        missing_downloads: set[VidEntry] = set(find_vids_missing_downloads)
        for vid in known_vids:
            if vid not in missing_downloads:
                out.append(vid)
        return out

    def download(
        self,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None = None,
    ) -> None:
        self.api.download(
            download_limit=download_limit, yt_dlp_uses_docker=yt_dlp_uses_docker
        )

    def sync(
        self,
        limit_scroll_pages: int,
        download_limit: int | None,
        yt_dlp_uses_docker: bool | None = None,
    ) -> None:
        vids: list[VidEntry] = self.scan_for_vids(limit_scroll_pages)
        self.library.merge(vids, save=True)
        self.download(download_limit, yt_dlp_uses_docker)


__all__ = ["YouTubeSync", "update_yt_dlp", "Source", "Library", "VidEntry"]
