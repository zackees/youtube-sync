import json
import re
import shutil
import subprocess
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .cookies import Cookies
from .types import ChannelId, VideoId

# yt-dlp-ChromeCookieUnlock

# https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file


_COOKIE_REFRESH_HOURS = 2


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


def fetch_channel_info_ytdlp(
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


def fetch_video_info(
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
        cmd_list.insert(2, "--cookies")
        cmd_list.insert(3, cookies_txt.as_posix())
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


def fetch_channel_url_ytdlp(
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
    if cookies_txt is not None:
        cmd_list.insert(2, "--cookies")
        cmd_list.insert(3, cookies_txt.as_posix())
    completed_proc = subprocess.run(
        cmd_list, capture_output=True, text=True, timeout=10, shell=False, check=True
    )
    if completed_proc.returncode != 0:
        stderr = completed_proc.stderr
        warnings.warn(f"Failed to run yt-dlp with args: {cmd_list}, stderr: {stderr}")
    lines = completed_proc.stdout.splitlines()
    out_lines: list[str] = []
    for line in lines:
        if line.startswith("OSError:"):  # happens on zach's machine
            continue
        out_lines.append(line)
    out = "\n".join(out_lines)
    return out


def fetch_channel_id_ytdlp(
    video_url: str, yt_exe: Path | None = None, cookies_txt: Path | None = None
) -> ChannelId:
    """Fetch the info."""
    url = fetch_channel_url_ytdlp(
        video_url=video_url, yt_exe=yt_exe, cookies_txt=cookies_txt
    )
    match = re.search(r"/channel/([^/]+)/?", url)
    if match:
        out: str = str(match.group(1))
        return ChannelId(out)
    raise RuntimeError(f"Could not find channel id in: {video_url} using yt-dlp.")


def fetch_videos_from_channel(
    channel_url: str, yt_exe: Path | None = None
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


def fetch_videos_from_youtube_channel(
    channel_id: str, yt_exe: Path | None = None
) -> list[VideoId]:
    """Fetch the videos from a youtube channel."""
    channel_url = f"https://www.youtube.com/channel/{channel_id}"
    return fetch_videos_from_channel(channel_url, yt_exe)


def _is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def _get_or_refresh_cookies(
    url: str, cookies_pkl: Path, refresh_time: int, cookies: Cookies | None
) -> Cookies:
    now = datetime.now()
    if cookies is not None:
        expire_time = cookies.creation_time + timedelta(hours=refresh_time)
        if now < expire_time:
            return cookies
    elif cookies_pkl.exists():
        yt_cookies = Cookies.load(cookies_pkl)
        hours_old = (yt_cookies.creation_time - yt_cookies.creation_time).seconds / 3600
        if hours_old < refresh_time:
            return yt_cookies
    # refresh
    yt_cookies = Cookies.from_browser(url)
    yt_cookies.save(cookies_pkl)
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
            refresh_time=_COOKIE_REFRESH_HOURS,
            cookies=self.youtube_cookies,
        )
        return self.youtube_cookies_txt

    def fetch_channel_info(self, video_url: str) -> dict[Any, Any]:
        cookies = self._extract_cookies_if_needed(video_url)
        return fetch_channel_info_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def fetch_video_info(self, video_url: str) -> dict:
        cookies = self._extract_cookies_if_needed(video_url)
        return fetch_video_info(
            video_url,
            yt_exe=self.yt_exe,
            cookies_txt=cookies,
        )

    def fetch_channel_url(self, video_url: str) -> str:
        cookies = self._extract_cookies_if_needed(video_url)
        return fetch_channel_url_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )

    def fetch_channel_id(self, video_url: str) -> ChannelId:
        cookies = self._extract_cookies_if_needed(video_url)
        return fetch_channel_id_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies
        )
