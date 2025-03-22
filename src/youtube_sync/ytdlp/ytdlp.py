import _thread
import json
import os
import re
import shutil
import signal
import subprocess
import time
import warnings
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from youtube_sync.cookies import Cookies
from youtube_sync.types import ChannelId, Source, VideoId
from youtube_sync.uploader import Uploader

from .downloader import YtDlpDownloader
from .error import (
    KeyboardInterruptException,
    check_keyboard_interrupt,
    set_keyboard_interrupt,
)

# yt-dlp-ChromeCookieUnlock

# https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file


def yt_dlp_exe(install_missing_plugins=True) -> Path | Exception:
    yt_exe = shutil.which("yt-dlp")
    if yt_exe is None:
        return FileNotFoundError("yt-dlp not found")
    if install_missing_plugins:
        from youtube_sync.ytdlp.plugins import yt_dlp_install_plugins

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


def yt_dlp_download_best_audio(
    yt_exe: Path,
    url: str,
    temp_dir: Path,
    cookies_txt: Path | None,
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

    # def fetch_videos_from_channel(self, channel_url: str) -> list[VideoId]:
    #     cookies_txt = self._extract_cookies_if_needed()
    #     return _fetch_videos_from_channel(
    #         channel_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
    #     )

    def _process_conversion(
        self, downloader: YtDlpDownloader, uploader: Uploader
    ) -> tuple[str, str, Exception | None]:
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
            downloader.copy_to_destination(uploader)
            return (downloader.url, downloader.outmp3, None)
        except Exception as e:
            return (downloader.url, downloader.outmp3, e)
        finally:
            # Clean up resources
            downloader.dispose()

    def download_mp3s(
        self,
        downloads: list[tuple[str, str]],
        download_pool: ThreadPoolExecutor,
        uploader: Uploader,
    ) -> list[Future[tuple[str, str, Exception | None]]]:
        from youtube_sync.ytdlp.bulk_download_mp3s import download_mp3s

        return download_mp3s(
            self,
            downloads,
            download_pool,
            uploader,
        )

    def download_mp3(self, url: str, outmp3: str, uploader: Uploader) -> None:
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
                uploader=uploader,
            )

            # Wait for the single future to complete
            assert len(futures) == 1
            future = futures[0]

            # Get the result and raise any exception
            _, _, error = future.result()
            if error is not None:
                raise error
