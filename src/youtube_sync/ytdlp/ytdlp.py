import json
import re
import subprocess
import warnings
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from youtube_sync import FSPath
from youtube_sync.cookies import Cookies
from youtube_sync.types import ChannelId, Source
from youtube_sync.ytdlp.exe import YtDlpCmdRunner


def yt_dlp_verbose(yt_exe: Path | None = None) -> str | Exception:
    """Get yt-dlp verbose output."""
    if yt_exe is None:
        cmd_runner = YtDlpCmdRunner.create()
        if isinstance(cmd_runner, Exception):
            return cmd_runner
        exe = cmd_runner.exe
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

    from .exe import YtDlpCmdRunner

    if yt_exe is None:
        cmd_runner = YtDlpCmdRunner.create_or_raise()
        yt_exe = cmd_runner.exe

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
    video_url: str, yt_exe: Path, cookies_txt: Path | None = None
) -> dict:
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
    from .exe import YtDlpCmdRunner

    if yt_exe is None:
        cmd_runnner = YtDlpCmdRunner.create_or_raise()
        yt_exe = cmd_runnner.exe
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


class YtDlp:

    def __init__(self, source: Source) -> None:
        self.source: Source = source
        self.yt_cmd_runner = YtDlpCmdRunner.create_or_raise()
        self.yt_exe: Path = self.yt_cmd_runner.exe
        self.cookies: Cookies | None = None

    def _extract_cookies_if_needed(self) -> Cookies | None:
        if self.source == Source.YOUTUBE:
            self.cookies = Cookies.load(self.source)
            return self.cookies
        return None

    def fetch_channel_info(self, video_url: str) -> dict[Any, Any]:
        cookies = self._extract_cookies_if_needed()
        # cookies_txt = cookies.path_txt if cookies is not None else None
        cookies_txt: Path | None = (
            Path(cookies.path_txt) if cookies is not None else None
        )
        return _fetch_channel_info_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def fetch_video_info(self, video_url: str) -> dict:
        cookies = self._extract_cookies_if_needed()
        # cookies_txt = cookies.path_txt if cookies is not None else None
        cookies_txt: Path | None = (
            Path(cookies.path_txt) if cookies is not None else None
        )
        return _fetch_video_info(
            video_url,
            yt_exe=self.yt_exe,
            cookies_txt=cookies_txt,
        )

    def fetch_channel_url(self, video_url: str) -> str:
        cookies = self._extract_cookies_if_needed()
        # cookies_txt = cookies.path_txt if cookies is not None else None
        cookies_txt: Path | None = (
            Path(cookies.path_txt) if cookies is not None else None
        )
        return _fetch_channel_url_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def fetch_channel_id(self, video_url: str) -> ChannelId:
        cookies = self._extract_cookies_if_needed()
        cookies_txt: Path | None = (
            Path(cookies.path_txt) if cookies is not None else None
        )
        return _fetch_channel_id_ytdlp(
            video_url, yt_exe=self.yt_exe, cookies_txt=cookies_txt
        )

    def download_mp3s(
        self,
        downloads: list[tuple[str, FSPath]],
        download_pool: ThreadPoolExecutor,
    ) -> list[Future[tuple[str, FSPath, Exception | None]]]:
        from youtube_sync.ytdlp.bulk_download_mp3s import download_mp3s

        cookies = self._extract_cookies_if_needed()

        return download_mp3s(
            downloads,
            download_pool,
            cookies,
        )

    def download_mp3(self, url: str, outmp3: FSPath) -> None:
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
