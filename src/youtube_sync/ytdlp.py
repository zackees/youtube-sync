import _thread
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import warnings
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from static_ffmpeg import add_paths

from youtube_sync.types import Source

from .cookies import Cookies
from .types import ChannelId, VideoId

_MAX_CPU_WORKERS = max(1, os.cpu_count() or 0)

# Thread pool for resolving futures
_FUTURE_RESOLVER_POOL = ThreadPoolExecutor(
    max_workers=_MAX_CPU_WORKERS, thread_name_prefix="future_resolver"
)

_FFMPEG_EXECUTORS = ThreadPoolExecutor(
    _MAX_CPU_WORKERS, thread_name_prefix="ffmpeg_executor"
)


class KeyboardInterruptException(Exception):
    """Exception raised when a keyboard interrupt is detected."""

    pass


# Global flag to track keyboard interrupts
_KEYBOARD_INTERRUPT_HAPPENED = False


# Function to check and set the interrupt flag
def set_keyboard_interrupt():
    """Set the global keyboard interrupt flag."""
    global _KEYBOARD_INTERRUPT_HAPPENED
    _KEYBOARD_INTERRUPT_HAPPENED = True


def check_keyboard_interrupt():
    """Check if a keyboard interrupt has happened.

    Returns:
        bool: True if a keyboard interrupt has happened
    """
    return _KEYBOARD_INTERRUPT_HAPPENED


# yt-dlp-ChromeCookieUnlock

# https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file


_FFMPEG_PATH_ADDED = False


def yt_dlp_exe(install_missing_plugins=True) -> Path | Exception:
    yt_exe = shutil.which("yt-dlp")
    if yt_exe is None:
        return FileNotFoundError("yt-dlp not found")
    if install_missing_plugins:
        from youtube_sync.ytdlp_plugins import yt_dlp_install_plugins

        errors: dict[str, Exception] | None = yt_dlp_install_plugins()
        if errors:
            warnings.warn(f"Failed to install yt-dlp plugins: {errors}")
    return Path(yt_exe)


def yt_dlp_verbose(yt_exe: Path | None = None) -> str | Exception:
    """Get yt-dlp verbose output."""
    if yt_exe is None:
        exe = yt_dlp_exe()
        if isinstance(exe, Exception):
            return exe
    else:
        exe = yt_exe
    exe_str = exe.as_posix()
    cp = subprocess.run([exe_str, "--verbose"], capture_output=True)
    stdout_bytes = cp.stdout
    stderr_bytes = cp.stderr
    stdout = stdout_bytes.decode("utf-8") + stderr_bytes.decode("utf-8")
    return stdout


def _fetch_channel_info_ytdlp(
    video_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> dict[Any, Any]:
    """Fetch the info.

    Args:
        video_url: The URL of the video
        yt_exe: Optional path to yt-dlp executable
        cookies: Optional path to cookies file

    Returns:
        Dictionary containing channel information
    """
    # yt-dlp -J "VIDEO_URL" > video_info.json

    if yt_exe is None:
        yt_or_error = yt_dlp_exe()
        if isinstance(yt_or_error, Exception):
            raise yt_or_error
        yt_exe = yt_or_error

    cmd_list = [
        yt_exe.as_posix(),
        "-J",
    ]

    # Add cookies parameter if provided
    if cookies_txt is not None:
        cmd_list.extend(["--cookies", cookies_txt.as_posix()])

    cmd_list.append(video_url)
    completed_proc = subprocess.run(
        cmd_list, capture_output=True, text=True, shell=False, check=True
    )
    if completed_proc.returncode != 0:
        stderr = completed_proc.stderr
        warnings.warn(f"Failed to run yt-dlp with args: {cmd_list}, stderr: {stderr}")
    lines: list[str] = []
    for line in completed_proc.stdout.splitlines():
        if line.startswith("OSError:"):
            continue
        lines.append(line)
    out = "\n".join(lines)
    data = json.loads(out)
    return data


def _fetch_video_info(
    video_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> dict:
    if yt_exe is None:
        yt_or_error = yt_dlp_exe()
        if isinstance(yt_or_error, Exception):
            raise yt_or_error
        yt_exe = yt_or_error
    if isinstance(yt_exe, Exception):
        raise yt_exe
    cmd_list = [
        yt_exe.as_posix(),
        "-J",
        video_url,
    ]

    # Add cookies parameter if provided
    if cookies_txt is not None:
        cmd_list.append("--cookies")
        cmd_list.append(cookies_txt.as_posix())
    completed_proc = subprocess.run(
        cmd_list, capture_output=True, text=True, shell=False, check=True
    )
    if completed_proc.returncode != 0:
        stderr = completed_proc.stderr
        warnings.warn(f"Failed to run yt-dlp with args: {cmd_list}, stderr: {stderr}")
    lines: list[str] = []
    for line in completed_proc.stdout.splitlines():
        if line.startswith("OSError:"):
            continue
        lines.append(line)
    out = "\n".join(lines)
    data = json.loads(out)
    return data


def _fetch_channel_url_ytdlp(
    video_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> str:
    """Fetch the info."""
    # yt-dlp -J "VIDEO_URL" > video_info.json
    if yt_exe is None:
        yt_or_error = yt_dlp_exe()
        if isinstance(yt_or_error, Exception):
            raise yt_or_error
        yt_exe = yt_or_error
    cmd_list = [
        yt_exe.as_posix(),
        "--print",
        "channel_url",
        video_url,
    ]
    timeout = 10
    if cookies_txt is not None:
        cmd_list.append("--cookies")
        cmd_list.append(cookies_txt.as_posix())
    cmd_str = subprocess.list2cmdline(cmd_list)
    print(f"Running: {cmd_str}")
    completed_proc = subprocess.run(
        cmd_list,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    if completed_proc.returncode != 0:
        stdout = completed_proc.stdout + completed_proc.stderr
        msg = f"Failed to run yt-dlp with args: {cmd_str}\n  Return code: {completed_proc.returncode}\n  out: {stdout}"
        warnings.warn(msg)
        raise RuntimeError(msg)
    lines = completed_proc.stdout.splitlines()
    out_lines: list[str] = []
    for line in lines:
        if line.startswith("OSError:"):  # happens on zach's machine
            continue
        out_lines.append(line)
    out = "\n".join(out_lines)
    return out


def _fetch_channel_id_ytdlp(
    video_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> ChannelId:
    """Fetch the info."""
    url = _fetch_channel_url_ytdlp(
        video_url=video_url, yt_exe=yt_exe, cookies_txt=cookies_txt
    )
    match = re.search(r"/channel/([^/]+)/?", url)
    if match:
        out: str = str(match.group(1))
        return ChannelId(out)
    raise RuntimeError(f"Could not find channel id in: {video_url} using yt-dlp.")


def _fetch_videos_from_channel(
    channel_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> list[VideoId]:
    """Fetch the videos from a channel."""
    # yt-dlp -J "CHANNEL_URL" > channel_info.json
    # cmd = f'yt-dlp -i --get-id "https://www.youtube.com/channel/{channel_id}"'
    if yt_exe is None:
        yt_or_error = yt_dlp_exe()
        if isinstance(yt_or_error, Exception):
            raise yt_or_error
        yt_exe = yt_or_error
    cmd_list = [yt_exe.as_posix(), "--print", "id", channel_url]
    if cookies_txt is not None:
        cmd_list.append("--cookies")
        cmd_list.append(cookies_txt.as_posix())
    cms_str = subprocess.list2cmdline(cmd_list)
    print(f"Running: {cms_str}")
    completed_proc = subprocess.run(
        cmd_list,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    stdout = completed_proc.stdout
    lines = stdout.splitlines()
    out_channel_ids: list[VideoId] = []
    for line in lines:
        if line.startswith("OSError:"):  # happens on zach's machine
            continue
        if line.startswith("WARNING:"):
            warnings.warn(line)
            continue
        if line.startswith("ERROR:"):
            warnings.warn(line)
            continue
        out_channel_ids.append(VideoId(line))
    return out_channel_ids


def add_ffmpeg_paths_once() -> None:
    global _FFMPEG_PATH_ADDED  # pylint: disable=global-statement
    if not _FFMPEG_PATH_ADDED:
        add_paths()
        _FFMPEG_PATH_ADDED = True


def yt_dlp_download_best_audio(
    url: str,
    temp_dir: Path,
    cookies_txt: Path | None,
    yt_exe: Path | None = None,
    no_geo_bypass: bool = True,
    retries: int = 1,
) -> Path | Exception:
    """Download the best audio from a URL to a temporary directory without conversion.

    Args:
        url: The URL to download from
        temp_dir: Directory to save the temporary file
        cookies_txt: Path to cookies.txt file or None
        yt_exe: Path to yt-dlp executable or None to auto-detect
        no_geo_bypass: Whether to disable geo-bypass
        retries: Number of download attempts to make before giving up

    Returns:
        Path to the downloaded audio file or Exception if download failed
    """
    if check_keyboard_interrupt():
        return KeyboardInterruptException(
            "Download aborted due to previous keyboard interrupt"
        )

    if yt_exe is None:
        yt_exe_result = yt_dlp_exe()
        if isinstance(yt_exe_result, Exception):
            return yt_exe_result
        yt_exe = yt_exe_result

    # Use a generic name for the temporary file - let yt-dlp determine the extension
    temp_file = Path(os.path.join(temp_dir, "temp_audio"))

    # Command to download best audio format without any conversion
    cmd_list = [
        yt_exe.as_posix(),
        url,
        "-f",
        "bestaudio/worst",  # Select best audio format
        "--no-playlist",  # Don't download playlists
        "--output",
        f"{temp_file.as_posix()}.%(ext)s",  # Output filename pattern
    ]

    if no_geo_bypass:
        cmd_list.append("--no-geo-bypass")

    if cookies_txt is not None:
        cmd_list.extend(["--cookies", cookies_txt.as_posix()])

    ke: KeyboardInterrupt | None = None
    last_error: Exception | None = None

    for attempt in range(retries):
        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        try:
            proc = subprocess.Popen(cmd_list)
            while True:
                if proc.poll() is not None:
                    break
                if check_keyboard_interrupt():
                    proc.terminate()
                    return KeyboardInterruptException(
                        "Download aborted due to previous keyboard interrupt"
                    )
                time.sleep(0.1)

            if proc.returncode == 0:
                # Find the downloaded file (with whatever extension yt-dlp used)
                downloaded_files = list(temp_dir.glob("temp_audio.*"))
                if not downloaded_files:
                    last_error = FileNotFoundError(
                        f"No audio file was downloaded to {temp_dir}"
                    )
                    continue
                return downloaded_files[0]
            else:
                rtn = proc.returncode
                if 3221225786 == rtn or rtn == -signal.SIGINT:
                    set_keyboard_interrupt()
                    raise KeyboardInterrupt("KeyboardInterrupt")
                last_error = subprocess.CalledProcessError(
                    returncode=proc.returncode, cmd=cmd_list
                )
                print(f"Download attempt {attempt+1}/{retries} failed: {last_error}")

        except KeyboardInterrupt as kee:
            set_keyboard_interrupt()
            _thread.interrupt_main()
            ke = kee
            break
        except Exception as e:
            last_error = e
            print(f"Download attempt {attempt+1}/{retries} failed: {e}")

    if ke is not None:
        raise ke

    return last_error or RuntimeError(
        f"Failed to download {url} after {retries} attempts"
    )


def convert_audio_to_mp3(input_file: Path, output_file: Path) -> Path | Exception:
    """Convert audio file to MP3 format using ffmpeg.

    Args:
        input_file: Path to the input audio file
        output_file: Path to save the output MP3 file

    Returns:
        Path to the output MP3 file or Exception if conversion failed
    """
    if check_keyboard_interrupt():
        return KeyboardInterruptException(
            "Conversion aborted due to previous keyboard interrupt"
        )

    add_ffmpeg_paths_once()

    # Ensure the output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd_list = [
        "ffmpeg",
        "-i",
        str(input_file),
        "-codec:a",
        "libmp3lame",
        "-qscale:a",
        "2",  # High quality setting
        "-y",  # Overwrite output file if it exists
        str(output_file),
    ]

    try:
        print(f"Begin {input_file} -> {output_file}")
        # proc = subprocess.Popen(cmd_list)
        # pipe to devnull to suppress output
        proc = subprocess.Popen(
            cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Monitor the process and check for interrupts
        while proc.poll() is None:
            if check_keyboard_interrupt():
                proc.terminate()
                return KeyboardInterruptException(
                    "Conversion aborted due to previous keyboard interrupt"
                )
            time.sleep(0.1)

        if proc.returncode != 0:
            rtn = proc.returncode
            if 3221225786 == rtn or rtn == -signal.SIGINT:
                set_keyboard_interrupt()
                raise KeyboardInterrupt("KeyboardInterrupt")

            return subprocess.CalledProcessError(proc.returncode, cmd_list)
        print(f"Conversion successful: {input_file} -> {output_file}")
        return output_file
    except KeyboardInterrupt:
        set_keyboard_interrupt()
        _thread.interrupt_main()
        raise
    except subprocess.CalledProcessError as e:
        return e


class YtDlpDownloader:
    """Class for downloading and converting YouTube videos to MP3."""

    def __init__(self, url: str, outmp3: Path, cookies_txt: Path | None = None):
        """Initialize the downloader with a temporary directory and download parameters.

        Args:
            url: The URL to download from
            outmp3: Path to save the final MP3 file
            cookies_txt: Path to cookies.txt file or None
        """
        add_ffmpeg_paths_once()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self._temp_dir.name)
        self.url = url
        self.outmp3 = outmp3
        self.cookies_txt = cookies_txt
        self.downloaded_file: Path | None = None
        self.temp_mp3: Path | None = None

        # Ensure output directory exists
        par_dir = os.path.dirname(str(outmp3))
        if par_dir:
            os.makedirs(par_dir, exist_ok=True)

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
        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        yt_exe = yt_dlp_exe()
        if isinstance(yt_exe, Exception):
            return yt_exe

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
        shutil.copy(str(self.temp_mp3), str(self.outmp3))


def _is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


class YtDlp:

    def __init__(self, source: Source) -> None:
        self.source: Source = source
        yt_exe = yt_dlp_exe()
        if isinstance(yt_exe, Exception):
            raise yt_exe
        self.yt_exe: Path = yt_exe
        self.cookies: Cookies | None = None

    def _extract_cookies_if_needed(self) -> Path | None:
        if self.source == Source.YOUTUBE:
            self.cookies = Cookies.load(self.source)
            return self.cookies.path_txt
        return None

    def fetch_channel_info(self, video_url: str) -> dict[Any, Any]:
        cookies_txt = self._extract_cookies_if_needed()
        return _fetch_channel_info_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def fetch_video_info(self, video_url: str) -> dict:
        cookies_txt = self._extract_cookies_if_needed()
        return _fetch_video_info(
            video_url,
            yt_exe=self.yt_exe,
            cookies_txt=cookies_txt,
        )

    def fetch_channel_url(self, video_url: str) -> str:
        cookies_txt = self._extract_cookies_if_needed()
        return _fetch_channel_url_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def fetch_channel_id(self, video_url: str) -> ChannelId:
        cookies_txt = self._extract_cookies_if_needed()
        return _fetch_channel_id_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def fetch_videos_from_channel(self, channel_url: str) -> list[VideoId]:
        cookies_txt = self._extract_cookies_if_needed()
        return _fetch_videos_from_channel(
            channel_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def _process_conversion(
        self, downloader: YtDlpDownloader
    ) -> tuple[str, Path, Exception | None]:
        """Process conversion and copying for a downloaded file.

        Args:
            downloader: The YtDlpDownloader instance with a downloaded file

        Returns:
            Tuple of (url, output_path, exception_or_none)
        """
        try:
            # Convert to MP3
            convert_result = downloader.convert_to_mp3()
            if isinstance(convert_result, Exception):
                return (downloader.url, downloader.outmp3, convert_result)

            # Copy to destination
            downloader.copy_to_destination()
            return (downloader.url, downloader.outmp3, None)
        except Exception as e:
            return (downloader.url, downloader.outmp3, e)
        finally:
            # Clean up resources
            downloader.dispose()

    def download_mp3s(
        self,
        downloads: list[tuple[str, Path]],
        download_pool: ThreadPoolExecutor,
    ) -> list[Future[tuple[str, Path, Exception | None]]]:
        """Download multiple YouTube videos as MP3s using thread pools.

        Args:
            downloads: List of tuples containing (url, output_path)
            download_pool: Thread pool for downloads
            convert_pool: Thread pool for conversions

        Returns:
            List of futures that will resolve to tuples of (url, output_path, exception_or_none)
            where exception_or_none is None if download was successful,
            or the exception that occurred during download
        """
        result_futures: list[Future[tuple[str, Path, Exception | None]]] = []

        # Process each download
        for i, (url, outmp3) in enumerate(downloads):
            # Create a future that will represent the final result for this download
            def on_done_task(count=i) -> None:
                print(f"Download {count+1}/{len(downloads)} complete")

            result_future: Future[tuple[str, Path, Exception | None]] = Future()
            result_futures.append(result_future)
            result_future.add_done_callback(lambda _: on_done_task)

            # Extract cookies if needed
            cookies = self._extract_cookies_if_needed()

            # Submit the entire download and conversion process as a single task
            _FUTURE_RESOLVER_POOL.submit(
                self._process_download_and_convert,
                url,
                outmp3,
                cookies,
                download_pool,
                result_future,
            )

        return result_futures

    def _process_download_and_convert(
        self,
        url: str,
        outmp3: Path,
        cookies: Path | None,
        download_pool: ThreadPoolExecutor,
        result_future: Future[tuple[str, Path, Exception | None]],
    ) -> None:
        """Process the download and conversion for a single URL.

        Args:
            url: The URL to download
            outmp3: Path to save the final MP3 file
            cookies: Path to cookies file or None
            download_pool: Thread pool for downloads
            convert_pool: Thread pool for conversions
            result_future: Future to set with the final result
        """
        # Create downloader
        downloader = YtDlpDownloader(url, outmp3, cookies)

        try:
            # Check for keyboard interrupt
            if check_keyboard_interrupt():
                result_future.set_result(
                    (
                        url,
                        outmp3,
                        KeyboardInterruptException(
                            "Download aborted due to previous keyboard interrupt"
                        ),
                    )
                )
                return

            # Submit download task and wait for it to complete
            download_future = download_pool.submit(downloader.download)
            download_result = download_future.result()

            # If download failed, set the result and return
            if isinstance(download_result, Exception):
                result_future.set_result((url, outmp3, download_result))
                return

            # Check for keyboard interrupt again before conversion
            if check_keyboard_interrupt():
                result_future.set_result(
                    (
                        url,
                        outmp3,
                        KeyboardInterruptException(
                            "Conversion aborted due to previous keyboard interrupt"
                        ),
                    )
                )
                return

            # Submit conversion task and wait for it to complete
            convert_future = _FFMPEG_EXECUTORS.submit(
                self._process_conversion, downloader
            )
            conversion_result = convert_future.result()

            # Set the final result
            result_future.set_result(conversion_result)

        except KeyboardInterrupt as e:
            # Handle keyboard interrupt
            set_keyboard_interrupt()
            result_future.set_result((url, outmp3, KeyboardInterruptException(str(e))))
            _thread.interrupt_main()
        except Exception as e:
            # Handle any other exceptions
            result_future.set_result((url, outmp3, e))
        finally:
            # Clean up resources
            downloader.dispose()

    def download_mp3(self, url: str, outmp3: Path) -> None:
        """Download a single YouTube video as MP3.

        Args:
            url: The URL to download from
            outmp3: Path to save the final MP3 file

        Raises:
            Exception: If download or conversion fails
        """
        # Create a single thread pool and use it for both download and conversion
        # to maintain sequential processing for a single file
        with (ThreadPoolExecutor(max_workers=1) as download_pool,):
            futures = self.download_mp3s(
                [(url, outmp3)],
                download_pool=download_pool,
            )

            # Wait for the single future to complete
            assert len(futures) == 1
            future = futures[0]

            # Get the result and raise any exception
            _, _, error = future.result()
            if error is not None:
                raise error
