from virtual_fs import FSPath, RealFS, RemoteFS, Vfs

from .config import Channel
from .library import Library
from .types import Source
from .vid_entry import VidEntry
from .ytdlp.update import update_yt_dlp


class YouTubeSync:
    def __init__(
        self,
        channel_name: str,
        channel_id: str,
        media_output: str | FSPath,
        source: Source,
        library_path: FSPath | None = None,
        channel_url: str | None = None,
    ) -> None:
        from .sync import YouTubeSyncImpl

        if channel_url is not None:
            if "http" not in channel_url:
                raise ValueError(f"Invalid channel URL: {channel_url}")

        if not isinstance(media_output, FSPath):
            media_output = Vfs.begin(src=media_output)  # type: ignore[reportUnknownMemberType]

        self.impl = YouTubeSyncImpl(
            channel_name=channel_name,
            channel_id=channel_id,
            media_output=media_output,
            source=source,
            library_path=library_path,
            channel_url=channel_url,
        )
        # Fix items
        self.fixup_video_names()

    def fixup_video_names(self, refresh: bool = True) -> None:
        return self.impl.fixup_video_names(refresh=refresh)

    @property
    def library(self) -> Library:
        return self.impl.library

    @property
    def source(self) -> Source:
        return self.impl.source

    def find_vids_missing_downloads(
        self, refresh: bool = True
    ) -> list[VidEntry] | Exception:
        if refresh:
            self.impl.known_vids(refresh=True)
        out = self.library.find_missing_downloads()
        return out

    def known_vids(self, refresh: bool = True) -> list[VidEntry]:
        out = self.impl.known_vids(refresh=refresh)
        return out

    def scan_for_vids(
        self, limit: int | None, stop_on_duplicate_vids: bool = False
    ) -> list[VidEntry]:
        out = self.impl.scan_for_vids(
            limit=limit,
            stop_on_duplicate_vids=stop_on_duplicate_vids,
        )
        return out

    def find_vids_already_downloaded(self, refresh: bool = True) -> list[VidEntry]:
        out = self.impl.known_vids(refresh=refresh)
        return out

    def download(
        self,
        limit: int | None,
    ) -> None:
        self.impl.download(limit)

    def sync(
        self,
        scan_limit: int,
        download_limit: int | None,
    ) -> None:
        return self.impl.sync(scan_limit, download_limit)


__all__ = [
    "YouTubeSync",
    "update_yt_dlp",
    "Source",
    "Library",
    "VidEntry",
    "FSPath",
    "FSPath",
    "RealFS",
    "RemoteFS",
    "Channel",
    "Source",
]
