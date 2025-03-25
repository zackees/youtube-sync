import os
import tempfile
from pathlib import Path

# from youtube_sync.filesystem import FS
from youtube_sync import FSPath
from youtube_sync.ffmpeg import convert_audio_to_mp3
from youtube_sync.ffmpeg import init_once as ffmpeg_init_once

from .error import KeyboardInterruptException, check_keyboard_interrupt
from .exe import YtDlpCmdRunner


class YtDlpDownloader:
    """Class for downloading and converting YouTube videos to MP3."""

    def __init__(self, url: str, outmp3: FSPath, cookies_txt: Path | None = None):
        """Initialize the downloader with a temporary directory and download parameters.

        Args:
            url: The URL to download from
            outmp3: Path to save the final MP3 file
            cookies_txt: Path to cookies.txt file or None
        """
        ffmpeg_init_once()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self._temp_dir.name)
        self.url = url
        self.outmp3 = outmp3
        self.cookies_txt = cookies_txt
        self.downloaded_file: Path | None = None
        self.temp_mp3: Path | None = None

        # Ensure output directory exists
        par_dir = outmp3.parent
        if par_dir:
            # os.makedirs(par_dir, exist_ok=True)
            par_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        self.dispose()

    def dispose(self):
        """Clean up the temporary directory."""
        if hasattr(self, "_temp_dir") and self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None

    def download(self) -> Path | Exception:
        """Download the best audio from the URL.

        Returns:
            Path to the downloaded audio file or Exception if download failed
        """
        from .download_best_audio import yt_dlp_download_best_audio

        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        yt_exe: YtDlpCmdRunner = YtDlpCmdRunner.create_or_raise()

        result = yt_dlp_download_best_audio(
            url=self.url,
            temp_dir=self.temp_dir_path,
            cookies_txt=self.cookies_txt,
            yt_exe=yt_exe,
            no_geo_bypass=True,
            retries=3,
        )

        if not isinstance(result, Exception):
            self.downloaded_file = result

        return result

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

        print(f"Copying {self.temp_mp3} -> {self.outmp3}")

        data = self.temp_mp3.read_bytes()
        self.outmp3.write_bytes(data)
