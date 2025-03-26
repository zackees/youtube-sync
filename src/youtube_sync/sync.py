import logging

from rclone_api.fs import FSPath

from .create import create
from .library import Library
from .sync_impl import BaseSync
from .types import Source
from .vid_entry import VidEntry

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class YouTubeSyncImpl:
    def __init__(
        self,
        channel_name: str,
        media_output: FSPath,
        source: Source,
        library_path: FSPath | None = None,
        channel_url: str | None = None,
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
        self, limit: int | None, stop_on_duplicate_vids=False
    ) -> list[VidEntry]:
        remaining_to_download = self.find_vids_missing_downloads()
        if len(remaining_to_download) < 5:
            out: list[VidEntry] = self.api.scan_for_vids(
                limit=limit,
                stop_on_duplicate_vids=stop_on_duplicate_vids,
            )
            self.library.merge(out, save=True)
            return out
        else:
            logger.info("Skipping scan for vids, enough videos already downloaded")
            return []

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
        limit: int | None,
    ) -> None:
        self.api.download(limit=limit)

    def sync(
        self,
        scan_limit: int,
        download_limit: int | None,
    ) -> None:
        vids: list[VidEntry] = self.scan_for_vids(scan_limit)
        self.library.merge(vids, save=True)
        self.download(download_limit)
