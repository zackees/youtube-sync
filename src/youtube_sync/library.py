# pylint: disable=too-many-arguments

"""Library json module."""

import _thread
import os
import sys
import traceback
import warnings
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from appdirs import user_data_dir
from filelock import FileLock

from youtube_sync import FSPath, RealFS
from youtube_sync.library_data import LibraryData, Source
from youtube_sync.logutil import create_logger
from youtube_sync.to_channel_url import to_channel_url
from youtube_sync.vid_entry import VidEntry
from youtube_sync.ytdlp.download_request import DownloadRequest
from youtube_sync.ytdlp.ytdlp import YtDlp

logger = create_logger(__name__, "INFO")


def _get_library_json_lock_path() -> str:
    """Get the library json path."""
    out = os.path.join(user_data_dir("youtube-sync"), "library.json.lock")
    return out


_FILE_LOCK = FileLock(_get_library_json_lock_path())


def _find_missing_downloads(
    vids: list[VidEntry],
    dst_video_path: FSPath,
) -> list[VidEntry] | Exception:
    """Find missing downloads."""
    try:
        out: list[VidEntry] = []
        files, _ = dst_video_path.ls()
        files_set: set[str] = set(files)

        for vid in vids:
            file_path = vid.file_path
            if file_path in files_set:
                continue
            out.append(vid)
        all_have_a_date = all(vid.date for vid in out)
        if all_have_a_date:
            # sort oldest first
            out.sort(key=lambda vid: vid.date)  # type: ignore
        return out
    except Exception as e:
        return e


def _make_library(
    channel_name: str,
    channel_id: str,
    channel_url: str | None,  # None means auto-find
    source: Source,
    library_path: FSPath,
) -> "Library":
    if channel_url is not None:
        if "http" not in channel_url:
            raise ValueError(f"Invalid channel url: {channel_url}")
    url = channel_url or to_channel_url(source=source, channel_id=channel_id)
    if "http" not in url:
        raise ValueError(f"Invalid channel URL: {url}")
    if library_path.exists():
        raise FileExistsError(f"Library file already exists: {library_path}")
    library = Library(
        channel_name=channel_name,
        channel_url=url,
        source=source,
        json_path=library_path,
    )
    library.load()
    return library


class Library:
    """Represents the library"""

    def __init__(
        self,
        channel_name: str,
        channel_url: str,
        source: Source | str,
        json_path: FSPath | Path,
    ) -> None:
        logger.info(f"Creating library: {channel_name}")
        if isinstance(source, str):
            source = Source.from_str(source)
        if isinstance(json_path, Path):
            json_path = RealFS.from_path(json_path)
        self.filesystem = json_path.fs
        self.source = source
        self.ytdlp = YtDlp(source=source)
        self.channel_url = channel_url
        self.channel_name = channel_name
        self.json_path = json_path
        self.out_dir = json_path.parent
        self.load()
        if not isinstance(self.libdata, LibraryData):
            logger.error(f"Error loading library: {self.libdata}")
            raise ValueError(f"Error loading library: {self.libdata}")

    @property
    def path(self) -> FSPath:
        """Get the path."""
        return self.json_path

    @staticmethod
    def create(
        channel_name: str,
        channel_id: str,
        channel_url: str | None,  # None means auto-find
        media_output: FSPath,
        source: Source,
        # None means place the library at the root of the media_output
        library_path: FSPath | None = None,
    ) -> "Library":
        library_path = library_path or media_output / "library.json"
        out = _make_library(
            channel_name=channel_name,
            channel_id=channel_id,
            channel_url=channel_url,
            source=source,
            library_path=library_path,
        )
        return out

    @staticmethod
    def get_or_create(
        channel_name: str,
        channel_id: str,
        channel_url: str | None,  # None means auto-find
        media_output: FSPath,
        source: Source,
        # None means place the library at the root of the media_output
        library_path: FSPath | None = None,
    ) -> "Library":
        library_path = library_path or media_output / "library.json"
        if library_path.exists():
            library_or_err = Library.from_json(library_path)
            if isinstance(library_or_err, Library):
                logger.info(
                    f"Loaded library: {library_or_err} with channel url {library_or_err.channel_url}"
                )
                return library_or_err
            warnings.warn(
                f"Error loading library: {library_or_err}, falling back to create."
            )

        return Library.create(
            channel_name=channel_name,
            channel_id=channel_id,
            channel_url=channel_url,
            media_output=media_output,
            source=source,
            library_path=library_path,
        )

    @staticmethod
    def from_json(json_path: FSPath) -> "Library | Exception | FileNotFoundError":
        """Create from json."""
        with _FILE_LOCK:
            lib_or_err = LibraryData.from_json(json_path)
        if not isinstance(lib_or_err, LibraryData):
            return lib_or_err
        libdata = lib_or_err
        if "http" not in libdata.channel_url:
            logger.error(f"Invalid channel URL: {libdata.channel_url}")
            if libdata.source == Source.YOUTUBE and not libdata.channel_url.startswith(
                "http"
            ):
                logger.error("Recoverable error, fixing channel URL")
                channel_id = libdata.channel_url
                if not channel_id.startswith("@"):
                    logger.error(f"Fixing channel ID: {channel_id} by prepending @")
                    channel_id = f"@{channel_id}"
                libdata.channel_url = to_channel_url(libdata.source, channel_id)
        channel_name = libdata.channel_name
        channel_url = libdata.channel_url
        source = libdata.source
        return Library(
            channel_name=channel_name,
            channel_url=channel_url,
            source=source,
            json_path=json_path,
        )

    def __repr__(self) -> str:
        return self.libdata.to_json_str()

    def __str__(self) -> str:
        return self.libdata.to_json_str()

    def __eq__(self, value):
        if not isinstance(value, Library):
            return False
        return self.libdata == value.libdata

    def _empty_data(self) -> LibraryData:
        return LibraryData(
            channel_name=self.channel_name,
            channel_url=self.channel_url,
            source=self.source,
            vids=[],
        )

    def known_vids(self, load=True) -> list[VidEntry]:
        """Get the downloaded vids."""
        if load:
            self.load()
        assert self.libdata is not None
        return self.libdata.vids.copy()

    def find_missing_downloads(self) -> list[VidEntry] | Exception:
        """Find missing downloads."""
        return _find_missing_downloads(self.libdata.vids, self.out_dir)

    def load(self) -> list[VidEntry]:
        """Load json from file."""
        # self.libdata = _load_json(self.library_json_path)
        # return self.libdata.vids
        with _FILE_LOCK:
            lib_or_err = LibraryData.from_json(self.json_path)
        if isinstance(lib_or_err, FileNotFoundError):
            lib_or_err = self._empty_data()
            self.libdata = lib_or_err
        elif isinstance(lib_or_err, Exception):
            logger.error(f"Error loading library: {lib_or_err}")
            raise lib_or_err
        elif isinstance(lib_or_err, LibraryData):
            self.libdata = lib_or_err
        else:
            logger.error(f"Unexpected return type {type(lib_or_err)}")
            raise ValueError(f"Unexpected return type {type(lib_or_err)}")
        assert isinstance(lib_or_err, LibraryData)
        lib: LibraryData = lib_or_err
        assert self.channel_name == lib.channel_name
        resave = False
        if self.channel_url != lib.channel_url:
            logger.warning(
                f"Channel URL mismatch: {self.channel_url} != {lib.channel_url}"
            )
            if not lib.channel_url.startswith("http") and self.channel_url.startswith(
                "http"
            ):
                logger.warning("Libdata had old error channel URL, fixing")
                lib.channel_url = self.channel_url
                resave = True
            else:
                logger.error("Channel URL mismatch, aborting")
                raise ValueError("Channel URL mismatch")
        # assert self.channel_url == lib_or_err.channel_url
        assert self.source == lib.source
        self.channel_name = self.libdata.channel_name
        self.channel_url = self.libdata.channel_url
        self.source = self.libdata.source
        if resave:
            self.save(overwrite=True)
        return self.libdata.vids.copy()

    def to_json(self) -> dict:
        """Convert to dictionary."""
        data = self.libdata or self._empty_data()
        out = data.to_json()
        return out

    def save(self, overwrite=False) -> Exception | None:
        """Save json to file."""
        data = self.libdata or self._empty_data()
        text = data.to_json_str()
        with _FILE_LOCK:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            if self.json_path.exists() and not overwrite:
                return FileExistsError(f"{self.json_path} exists.")
            self.json_path.write_text(text, encoding="utf-8")
        return None

    def merge(self, vids: list[VidEntry], save: bool) -> None:
        """Merge the vids into the library."""
        logger.info(f"Merging {len(vids)} vids into library for {self.channel_name}")
        self.load()
        assert self.libdata is not None
        self.libdata.merge(vids)
        if save:
            self.save(overwrite=True)

    def download_missing(
        self,
        limit: int | None,
        max_concurrent_downloads: int = 1,
    ) -> None:
        """Download the missing files using thread pools.

        Args:
            limit: Maximum number of files to download or None for unlimited
            max_concurrent_downloads: Maximum number of concurrent downloads
            max_concurrent_conversions: Maximum number of concurrent conversions
        """
        logger.info(f"Downloading missing files for {self.channel_name}")
        from youtube_sync.final_result import FinalResult
        from youtube_sync.ytdlp.error import (
            check_keyboard_interrupt,
            set_keyboard_interrupt,
        )

        # Create thread pools with appropriate sizes
        download_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_downloads, thread_name_prefix="download"
        )

        try:
            download_count = 0
            max_errors = 100

            # Check for keyboard interrupt
            if check_keyboard_interrupt():
                print("Detected previous keyboard interrupt. Aborting downloads.")
                return

            if (limit is not None) and (download_count >= limit):
                return

            # Find missing downloads
            print(
                "\n#######################\n# Scanning for missing files\n###################"
            )
            missing_downloads_or_error = self.find_missing_downloads()

            batch_size: int
            if isinstance(missing_downloads_or_error, Exception):
                logger.error(
                    f"Error finding missing downloads: {missing_downloads_or_error}"
                )
                return

            missing_downloads: list[VidEntry] = missing_downloads_or_error

            # Determine how many to download in this batch
            remaining_limit = None if limit is None else limit - download_count
            batch_size = (
                len(missing_downloads)
                if remaining_limit is None
                else min(len(missing_downloads), remaining_limit)
            )

            if batch_size <= 0:
                return

            # Prepare download list
            downloads_to_process: list[DownloadRequest] = []
            for i in range(batch_size):
                vid = missing_downloads[i]
                next_url = vid.url
                next_mp3_path = self.out_dir / vid.file_path
                di: DownloadRequest = DownloadRequest(
                    url=next_url,
                    outmp3=next_mp3_path,
                    download_vid=True,
                    download_date=True,
                )
                downloads_to_process.append(di)

            print(
                f"\n#######################\n# Downloading {batch_size} missing files\n"
                "###################"
            )

            try:
                # Submit downloads to thread pools
                futures: list[Future[FinalResult]] = self.ytdlp.download_mp3s(
                    downloads=downloads_to_process,
                    download_pool=download_pool,
                )
                if not futures:
                    print("No downloads to process. Exiting.")
                    return

                # Process results as they complete
                for i, future in enumerate(futures):
                    # Check for keyboard interrupt
                    if check_keyboard_interrupt():
                        print(
                            "Detected keyboard interrupt. Skipping remaining results."
                        )
                        return

                    vid = missing_downloads[i]
                    try:
                        final_result: FinalResult = future.result()
                        error = final_result.exception
                        if final_result.date is not None:
                            vid.date_upload = final_result.date
                            self.merge([vid], save=True)
                        if error is not None:
                            print(f"Error downloading {vid.url}: {error}")
                            self.mark_error(vid)
                            max_errors -= 1
                            if max_errors <= 0:
                                print("Too many errors, aborting downloads.")
                                download_pool.shutdown(wait=False, cancel_futures=True)
                                break
                        else:
                            print(f"Successfully downloaded {vid.url}")
                    except KeyboardInterrupt:
                        print(
                            "KeyboardInterrupt detected while processing results. Stopping download."
                        )
                        set_keyboard_interrupt()
                        return
                    except Exception as e:  # pylint: disable=broad-except
                        stacktrace_str = traceback.format_exc()
                        print(f"Error downloading {vid.url}: {e}")
                        print(stacktrace_str)
                        self.mark_error(vid)

                # Update download count
                download_count += batch_size

                # Check for keyboard interrupt after batch
                if check_keyboard_interrupt():
                    print(
                        "Detected keyboard interrupt after batch. Stopping downloads."
                    )
                    return

            except KeyboardInterrupt:
                print(
                    "KeyboardInterrupt detected. Stopping download and shutting down thread pools."
                )
                set_keyboard_interrupt()
                # Don't raise here, let the outer try/finally handle cleanup
                return

        except KeyboardInterrupt:
            print("KeyboardInterrupt detected. Shutting down thread pools.")
            set_keyboard_interrupt()
        finally:
            # Ensure pools are shut down properly
            print("Shutting down download pool...")
            download_pool.shutdown(wait=False, cancel_futures=True)

            # Re-raise KeyboardInterrupt to notify the main thread
            if sys.exc_info()[0] is KeyboardInterrupt:
                _thread.interrupt_main()
                raise

    def mark_error(self, vid: VidEntry) -> None:
        """Mark the vid as an error."""
        vid.error = True
        self.merge([vid], save=True)
        print(f"Marked {vid.url} as an error.")

    def date_range(self) -> tuple[datetime, datetime] | None:
        """Get the date range."""
        vids = self.load()
        dates = [vid.date for vid in vids if vid.date]
        if not dates:
            return None
        return min(dates), max(dates)
