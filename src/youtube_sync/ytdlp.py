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


def _get_ytdlp_command_mp3_download(
    yt_exe: Path,
    url: str,
    out_file: Path,
    update: bool,
    no_geo_bypass: bool,
    cookies_txt: Path | None,
) -> list[str]:
    add_ffmpeg_paths_once()
    is_youtube = "youtube.com" in url or "youtu.be" in url
    if is_youtube:
        assert cookies_txt is not None, "cookies_txt must be provided for youtube.com"
    if cookies_txt is not None:
        assert cookies_txt.exists(), f"cookies_txt does not exist: {cookies_txt}"
    cmd_list: list[str] = []
    cmd_list += [
        yt_exe.as_posix(),
        url,
    ]
    if is_youtube:
        cmd_list += [
            "-f",
            "bestaudio",
        ]
    cmd_list += [
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--output",
        out_file.as_posix(),
    ]
    if update:
        cmd_list.append("--update")
    if no_geo_bypass:
        cmd_list.append("--no-geo-bypass")
    if cookies_txt:
        cmd_list.append("--cookies")
        cmd_list.append(cookies_txt.as_posix())
    return cmd_list


def yt_dlp_download_mp3(url: str, outmp3: Path, cookies_txt: Path | None) -> None:
    """Download the youtube video as an mp3."""
    add_ffmpeg_paths_once()
    par_dir = os.path.dirname(str(outmp3))
    if par_dir:
        os.makedirs(par_dir, exist_ok=True)

    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe

    # yt_exe_str = yt_exe.as_posix()
    ke: KeyboardInterrupt | None = None
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "temp.mp3")
        for _ in range(3):
            try:
                cmd_list: list[str] = _get_ytdlp_command_mp3_download(
                    yt_exe=yt_exe,
                    url=url,
                    out_file=Path(temp_file),
                    no_geo_bypass=True,
                    update=False,
                    cookies_txt=cookies_txt,
                )
                cmd_str = subprocess.list2cmdline(cmd_list)
                print(f"Running: {cmd_str}")
                # subprocess.run(cmd_list, check=True)
                proc = subprocess.Popen(cmd_list)
                while True:
                    # proc.wait(timeout=.1)
                    if proc.poll() is not None:
                        break
                    time.sleep(0.1)

                shutil.copy(temp_file, outmp3)
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
