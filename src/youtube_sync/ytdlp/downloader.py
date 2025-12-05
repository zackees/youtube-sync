import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from virtual_fs import FSPath

# from youtube_sync.filesystem import FS
from youtube_sync.config import Source
from youtube_sync.ffmpeg import convert_audio_to_mp3
from youtube_sync.ffmpeg import init_once as ffmpeg_init_once
from youtube_sync.final_result import DownloadRequest

from .error import KeyboardInterruptException, check_keyboard_interrupt
from .exe import YtDlpCmdRunner


@dataclass
class DownloadResult:
    """Class to hold the result of a download operation."""

    di: DownloadRequest
    upload_date: datetime | None
    downloaded_mp3: Path | None


class YtDlpDownloader:
    """Class for downloading and converting YouTube videos to MP3."""

    def __init__(
        self, di: DownloadRequest, source: Source, cookies_txt: Path | None = None
    ):
        """Initialize the downloader with a temporary directory and download parameters.

        Args:
            url: The URL to download from
            outmp3: Path to save the final MP3 file
            cookies_txt: Path to cookies.txt file or None
        """
        ffmpeg_init_once()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self._temp_dir.name)
        # self.url = url
        # self.outmp3 = outmp3
        self.di = di
        self.cookies_txt = cookies_txt
        self.downloaded_file: Path | None = None
        self.temp_mp3: Path | None = None
        self.source = source
        self.date: datetime | Exception | None = None

        # Ensure output directory exists
        par_dir = self.di.outmp3.parent
        if par_dir:
            # os.makedirs(par_dir, exist_ok=True)
            par_dir.mkdir(parents=True, exist_ok=True)

    @property
    def url(self) -> str:
        """Return the URL to download."""
        return self.di.url

    @property
    def outmp3(self) -> FSPath:
        """Return the output MP3 path."""
        return self.di.outmp3

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Clean up resources when exiting context."""
        self.dispose()

    def dispose(self):
        """Clean up the temporary directory."""
        if hasattr(self, "_temp_dir") and self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None

    def download(self) -> DownloadResult | Exception:
        """Download the best audio from the URL.

        Returns:
            Path to the downloaded audio file or Exception if download failed
        """
        from .download_best_audio import (
            yt_dlp_download_best_audio,
        )
        from .download_video_upload_date import yt_dlp_get_upload_date

        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        yt_exe: YtDlpCmdRunner = YtDlpCmdRunner.create_or_raise()
        no_geo_bypass = True

        if self.di.download_vid:
            result = yt_dlp_download_best_audio(
                url=self.url,
                temp_dir=self.temp_dir_path,
                source=self.source,
                cookies_txt=self.cookies_txt,
                yt_exe=yt_exe,
                no_geo_bypass=no_geo_bypass,
                retries=3,
            )
            if isinstance(result, Exception):
                return result
            self.downloaded_file = result

        if self.di.download_date:
            date: datetime | Exception = yt_dlp_get_upload_date(
                yt_exe=yt_exe,
                source=self.source,
                url=self.url,
                cookies_txt=self.cookies_txt,
                no_geo_bypass=no_geo_bypass,
            )
            if isinstance(date, Exception):
                return date
            assert isinstance(date, datetime), "Date should be a datetime object"
            self.date = date

        date_or_none: datetime | None = None
        if isinstance(self.date, datetime):
            date_or_none = self.date
        return DownloadResult(
            di=self.di,
            upload_date=date_or_none,
            downloaded_mp3=self.downloaded_file,
        )

    def convert_to_mp3(self) -> Path | Exception:
        """Convert downloaded audio file to MP3 format.

        Returns:
            Path to the output MP3 file or Exception if conversion failed

        Raises:
            ValueError: If download() has not been called or failed
        """
        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Conversion aborted due to previous keyboard interrupt"
            )

        if self.downloaded_file is None:
            raise ValueError("No downloaded file available. Call download() first.")

        self.temp_mp3 = Path(os.path.join(self.temp_dir_path, "converted.mp3"))
        return convert_audio_to_mp3(self.downloaded_file, self.temp_mp3)

    def copy_to_destination(self) -> None:
        """Copy the converted MP3 to the final destination.

        Raises:
            ValueError: If convert_to_mp3() has not been called or failed
        """
        if check_keyboard_interrupt():
            raise KeyboardInterrupt("Copy aborted due to previous keyboard interrupt")

        if self.temp_mp3 is None:
            raise ValueError("No converted MP3 available. Call convert_to_mp3() first.")
        import time

        start = time.time()
        print(f"Copying {self.temp_mp3} -> {self.di.outmp3}")
        data = self.temp_mp3.read_bytes()
        self.di.outmp3.write_bytes(data)
        diff = time.time() - start
        print(
            f"\n#################################\n# Copy done in {diff:.2f} seconds: {self.outmp3}\n#################################\n"
        )
