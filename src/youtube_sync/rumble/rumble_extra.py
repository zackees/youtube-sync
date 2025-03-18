"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from pathlib import Path

from youtube_sync.library import Library
from youtube_sync.rumble.rumble import to_channel_url
from youtube_sync.types import VidEntry


# vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
def fetch_all_vids(channel_url: str, limit: int | None) -> list[VidEntry]:
    raise NotImplementedError("fetch_all_vids")


def rumble_library(
    channel_name: str,
    channel_url: str | None,  # None means auto-find
    media_output: Path,
    library_path: (
        Path | None
    ) = None,  # None means place the library in the media_output
) -> Library:
    url = channel_url or to_channel_url(channel_name)
    library_json = library_path or media_output / "library.json"
    library = Library(
        channel_name=channel_name,
        channel_url=url,
        source="youtube",
        json_path=library_json,
    )
    library.load()
    return library


def rumble_scan(
    library: Library,
    limit_scroll_pages: int | None,
) -> None:
    channel_url = library.channel_url
    vids: list[VidEntry] = fetch_all_vids(channel_url, limit=limit_scroll_pages)
    library.merge(vids, save=True)
    print(f"Updated {library.path}")


def rumble_download_missing(
    library: Library, download_limit: int | None, yt_dlp_uses_docker: bool
) -> None:
    library.download_missing(
        download_limit=download_limit, yt_dlp_uses_docker=yt_dlp_uses_docker
    )


def rumble_sync(
    channel_name: str,
    media_output: Path,
    limit_scroll_pages: int | None,  # None means no limit
    download: bool,
    download_limit: int | None,
    scan: bool,
    library_path: (
        Path | None
    ) = None,  # None means place the library.json file in the media_output
    channel_url: str | None = None,  # None means auto-find
    yt_dlp_uses_docker: bool = False,
) -> Library:
    # library = youtube_library(Path(output))

    raise NotImplementedError("This function is not implemented yet.")
    # lib = youtube_library(
    #     channel_name=channel_name,
    #     channel_url=channel_url,
    #     media_output=media_output,
    #     library_path=library_path,
    # )
    # if scan:
    #     youtube_scan(library=lib, limit_scroll_pages=limit_scroll_pages)

    # if download:
    #     # lib.download_missing(download_limit)
    #     youtube_download_missing(
    #         library=lib,
    #         download_limit=download_limit,
    #         yt_dlp_uses_docker=yt_dlp_uses_docker,
    #     )

    # return lib
