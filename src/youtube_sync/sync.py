import logging

from virtual_fs import FSPath

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
        channel_id: str,
        media_output: FSPath,
        source: Source,
        library_path: FSPath | None = None,
        channel_url: str | None = None,
    ) -> None:
        library = Library.get_or_create(
            channel_name=channel_name,
            channel_url=channel_url,
            channel_id=channel_id,
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

    def fixup_video_names(self, refresh=True) -> None:
        if refresh:
            self.library.load()
        out = self.library.fixup_video_names()
        return out

    def find_vids_missing_downloads(self, refresh=True) -> list[VidEntry] | Exception:
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
        remaining_to_download: list[VidEntry] | Exception = (
            self.find_vids_missing_downloads()
        )
        do_scan: bool
        if isinstance(remaining_to_download, Exception):
            logger.warning(
                f"Failed to find vids missing downloads: {remaining_to_download}"
            )
            do_scan = True
        else:
            do_scan = len(remaining_to_download) < 5

        if do_scan:
            out: list[VidEntry] = self.api.scan_for_vids(
                limit=limit,
                stop_on_duplicate_vids=stop_on_duplicate_vids,
            )
            logger.info(f"Found {len(out)} new videos")
            self.library.merge(out, save=True)
            return out
        else:
            logger.info("Skipping scan for vids, enough videos already downloaded")
            return []

    def find_vids_already_downloaded(self, refresh=True) -> list[VidEntry]:
        known_vids = self.known_vids(refresh=refresh)
        find_vids_missing_downloads = self.find_vids_missing_downloads()
        if isinstance(find_vids_missing_downloads, Exception):
            return []
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
