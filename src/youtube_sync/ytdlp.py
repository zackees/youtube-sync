import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock
from static_ffmpeg import add_paths

from .cookies import Cookies
from .types import ChannelId, VideoId

# yt-dlp-ChromeCookieUnlock

# https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file


_COOKIE_REFRESH_HOURS = 2
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
        "bestaudio",  # Select best audio format
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
        try:
            proc = subprocess.Popen(cmd_list)
            while True:
                if proc.poll() is not None:
                    break
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
                last_error = subprocess.CalledProcessError(
                    returncode=proc.returncode, cmd=cmd_list
                )
                print(f"Download attempt {attempt+1}/{retries} failed: {last_error}")

        except KeyboardInterrupt as kee:
            import _thread

            _thread.interrupt_main()
            ke = kee
            break
        except subprocess.CalledProcessError as cpe:
            if 3221225786 == cpe.returncode or cpe.returncode == -signal.SIGINT:
                raise KeyboardInterrupt("KeyboardInterrupt")
            print(f"Failed to download {url}: {cpe}")
            last_error = cpe
            continue

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
        print(f"Convert {input_file} -> {output_file}")
        _ = subprocess.run(cmd_list, capture_output=True, check=True)
        return output_file
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
        if self.downloaded_file is None:
            raise ValueError("No downloaded file available. Call download() first.")

        self.temp_mp3 = Path(os.path.join(self.temp_dir_path, "converted.mp3"))
        return convert_audio_to_mp3(self.downloaded_file, self.temp_mp3)

    def copy_to_destination(self) -> None:
        """Copy the converted MP3 to the final destination.

        Raises:
            ValueError: If convert_to_mp3() has not been called or failed
        """
        if self.temp_mp3 is None:
            raise ValueError("No converted MP3 available. Call convert_to_mp3() first.")

        print(f"Copying {self.temp_mp3} -> {self.outmp3}")
        shutil.copy(str(self.temp_mp3), str(self.outmp3))


def _is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


_YOUTUBE_COOKIES_LOCK_PATH = Path("cookies") / "youtube" / "cookies.lock"
_YOUTUBE_COOKIES_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
_YOUTUBE_COOKIES_LOCK = FileLock(_YOUTUBE_COOKIES_LOCK_PATH)


def _get_or_refresh_cookies(
    url: str,
    cookies_pkl: Path,
    cookie_txt: Path,
    refresh_time: int,
    cookies: Cookies | None,
) -> Cookies:
    assert cookies_pkl.suffix == ".pkl"
    assert cookie_txt.suffix == ".txt"
    with _YOUTUBE_COOKIES_LOCK:
        now = datetime.now()
        if cookies is not None:
            expire_time = cookies.creation_time + timedelta(hours=refresh_time)
            if now < expire_time:
                return cookies
        elif cookies_pkl.exists() and cookie_txt.exists():
            yt_cookies = Cookies.load(cookies_pkl)
            hours_old = (
                yt_cookies.creation_time - yt_cookies.creation_time
            ).seconds / 3600
            if hours_old < refresh_time:
                return yt_cookies
        # refresh
        yt_cookies = Cookies.from_browser(url)
        yt_cookies.save(cookies_pkl)
        yt_cookies.save(cookie_txt)
        return yt_cookies


class YtDlp:

    def __init__(self) -> None:
        yt_exe = yt_dlp_exe()
        if isinstance(yt_exe, Exception):
            raise yt_exe
        self.yt_exe: Path = yt_exe
        self.youtube_cookies: Cookies | None = None
        self.youtube_cookies_txt: Path = Path("cookies") / "youtube" / "cookies.txt"
        self.youtube_cookies_pkl: Path = Path("cookies") / "youtube" / "cookies.pkl"

    def _extract_cookies_if_needed(self, url: str) -> Path | None:
        if not _is_youtube(url):
            return None
        self.youtube_cookies = _get_or_refresh_cookies(
            url="https://www.youtube.com",
            cookies_pkl=self.youtube_cookies_pkl,
            cookie_txt=self.youtube_cookies_txt,
            refresh_time=_COOKIE_REFRESH_HOURS,
            cookies=self.youtube_cookies,
        )
        return self.youtube_cookies_txt

    def fetch_channel_info(self, video_url: str) -> dict[Any, Any]:
        cookies = self._extract_cookies_if_needed(video_url)
        return _fetch_channel_info_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def fetch_video_info(self, video_url: str) -> dict:
        cookies = self._extract_cookies_if_needed(video_url)
        return _fetch_video_info(
            video_url,
            yt_exe=self.yt_exe,
            cookies_txt=cookies,
        )

    def fetch_channel_url(self, video_url: str) -> str:
        cookies = self._extract_cookies_if_needed(video_url)
        return _fetch_channel_url_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def fetch_channel_id(self, video_url: str) -> ChannelId:
        cookies = self._extract_cookies_if_needed(video_url)
        return _fetch_channel_id_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def fetch_videos_from_channel(self, channel_url: str) -> list[VideoId]:
        cookies = self._extract_cookies_if_needed(channel_url)
        return _fetch_videos_from_channel(
            channel_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def download_mp3s(
        self, downloads: list[tuple[str, Path]]
    ) -> list[tuple[str, Path, Exception | None]]:
        """Download multiple YouTube videos as MP3s.

        Args:
            downloads: List of tuples containing (url, output_path)

        Returns:
            List of tuples containing (url, output_path, exception_or_none)
            where exception_or_none is None if download was successful,
            or the exception that occurred during download
        """
        results: list[tuple[str, Path, Exception | None]] = []

        for url, outmp3 in downloads:
            cookies = self._extract_cookies_if_needed(url)
            try:
                with YtDlpDownloader(url, outmp3, cookies) as downloader:
                    # Step 1: Download
                    download_result = downloader.download()
                    if isinstance(download_result, Exception):
                        raise download_result

                    # Step 2: Convert
                    convert_result = downloader.convert_to_mp3()
                    if isinstance(convert_result, Exception):
                        raise convert_result

                    # Step 3: Copy to destination
                    downloader.copy_to_destination()

                results.append((url, outmp3, None))  # Success
            except Exception as e:
                results.append((url, outmp3, e))  # Failure

        return results

    def download_mp3(self, url: str, outmp3: Path) -> None:
        """Download a single YouTube video as MP3.

        Args:
            url: The URL to download from
            outmp3: Path to save the final MP3 file

        Raises:
            Exception: If download or conversion fails
        """
        results = self.download_mp3s([(url, outmp3)])
        assert len(results) == 1
        url, outmp3, error = results[0]
        if error is not None:
            raise error
