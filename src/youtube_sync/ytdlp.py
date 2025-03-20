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
) -> Path | Exception:
    """Download the best audio from a URL to a temporary directory without conversion.

    Args:
        url: The URL to download from
        temp_dir: Directory to save the temporary file
        cookies_txt: Path to cookies.txt file or None
        yt_exe: Path to yt-dlp executable or None to auto-detect
        no_geo_bypass: Whether to disable geo-bypass

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

    proc = subprocess.Popen(cmd_list)
    while True:
        if proc.poll() is not None:
            break
        time.sleep(0.1)

    if proc.returncode != 0:
        return subprocess.CalledProcessError(returncode=proc.returncode, cmd=cmd_list)

    # Find the downloaded file (with whatever extension yt-dlp used)
    downloaded_files = list(temp_dir.glob("temp_audio.*"))
    if not downloaded_files:
        return FileNotFoundError(f"No audio file was downloaded to {temp_dir}")

    return downloaded_files[0]


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


def yt_dlp_download_mp3(url: str, outmp3: Path, cookies_txt: Path | None) -> None:
    """Download the youtube video as an mp3."""
    add_ffmpeg_paths_once()
    par_dir = os.path.dirname(str(outmp3))
    if par_dir:
        os.makedirs(par_dir, exist_ok=True)

    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe

    ke: KeyboardInterrupt | None = None

    for _ in range(3):
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)

                # Step 1: Download the best audio
                audio_file = yt_dlp_download_best_audio(
                    url=url,
                    temp_dir=temp_dir_path,
                    cookies_txt=cookies_txt,
                    yt_exe=yt_exe,
                    no_geo_bypass=True,
                )

                if isinstance(audio_file, Exception):
                    raise audio_file

                # Step 2: Convert to MP3
                temp_mp3 = Path(os.path.join(temp_dir, "converted.mp3"))
                result = convert_audio_to_mp3(audio_file, temp_mp3)

                if isinstance(result, Exception):
                    raise result

                # Step 3: Copy to final destination
                print(f"Copying {temp_mp3} -> {outmp3}")
                shutil.copy(str(temp_mp3), str(outmp3))
                return
        except KeyboardInterrupt as kee:
            import _thread

            _thread.interrupt_main()
            ke = kee
            break
        except subprocess.CalledProcessError as cpe:
            if 3221225786 == cpe.returncode or cpe.returncode == -signal.SIGINT:
                raise KeyboardInterrupt("KeyboardInterrupt")
            print(f"Failed to download {url} as mp3: {cpe}")
            continue
    warnings.warn(f"Failed all attempts to download {url} as mp3.")
    if ke is not None:
        raise ke


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

    def download_mp3(self, url: str, outmp3: Path) -> None:
        cookies = self._extract_cookies_if_needed(url)
        yt_dlp_download_mp3(url, outmp3, cookies)
