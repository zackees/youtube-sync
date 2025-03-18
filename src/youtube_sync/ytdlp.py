import ast
import json
import re
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import Any

from .types import ChannelId, VideoId

# yt-dlp-ChromeCookieUnlock

# https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file


def yt_dlp_exe() -> Path | Exception:
    yt_exe = shutil.which("yt-dlp")
    if yt_exe is None:
        return FileNotFoundError("yt-dlp not found")
    return Path(yt_exe)


def yt_dlp_verbose() -> str | Exception:
    """Get yt-dlp verbose output."""
    exe = yt_dlp_exe()
    if isinstance(exe, Exception):
        return exe
    exe_str = exe.as_posix()
    cp = subprocess.run([exe_str, "--verbose"], capture_output=True)
    stdout_bytes = cp.stdout
    stderr_bytes = cp.stderr
    stdout = stdout_bytes.decode("utf-8") + stderr_bytes.decode("utf-8")
    return stdout


def _parse_plugin_dirs(stdout: str) -> list[Path]:
    """Parse plugin dirs."""
    lines = stdout.splitlines()
    for line in lines:
        if "Plugin directories" not in line:
            continue
        parts = line.split(":", maxsplit=1)
        # second part is the plugin dir value
        if len(parts) != 2:
            raise ValueError(f"Expected 2 parts, got {len(parts)}: {parts}")
        plugin_value = parts[1].strip()
        # this is now an array of string values like ['path1', 'path2']
        plugin_dirs = ast.literal_eval(plugin_value)
        # convert to Path
        return [Path(p) for p in plugin_dirs]
    raise ValueError(f"Could not find 'Plugin directories' in stdout: {stdout}")


def yt_dlp_plugin_dir() -> Path | Exception:
    """Get plugin directory."""
    exe = yt_dlp_exe()
    if isinstance(exe, Exception):
        return exe
    assert isinstance(exe, Path)

    try:
        cp = subprocess.run([exe, "--verbose"], capture_output=True)
        stdout_bytes = cp.stdout
        stderr_bytes = cp.stderr
        stdout = stdout_bytes.decode("utf-8") + stderr_bytes.decode("utf-8")
        assert (
            "yt-dlp" in stdout
        ), f"yt-dlp not in stdout: {stdout}, looks like an error"
        plugin_dirs = _parse_plugin_dirs(stdout)
        assert (
            len(plugin_dirs) > 0
        ), f"Expected at least one plugin dir, got {plugin_dirs}"
        return plugin_dirs[0]
    except Exception as e:
        import warnings

        warnings.warn(f"Failed to get plugin dir: {e}")
        return e


def fetch_channel_info_ytdlp(video_url: str) -> dict[Any, Any]:
    """Fetch the info."""
    # yt-dlp -J "VIDEO_URL" > video_info.json
    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe
    cmd_list = [
        yt_exe.as_posix(),
        "-J",
        video_url,
    ]
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


def fetch_video_info(video_url: str) -> dict:
    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe
    cmd_list = [
        yt_exe.as_posix(),
        "-J",
        video_url,
    ]
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


def fetch_channel_url_ytdlp(video_url: str) -> str:
    """Fetch the info."""
    # yt-dlp -J "VIDEO_URL" > video_info.json
    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe
    cmd_list = [
        yt_exe.as_posix(),
        "--print",
        "channel_url",
        video_url,
    ]
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


def fetch_channel_id_ytdlp(video_url: str) -> ChannelId:
    """Fetch the info."""
    url = fetch_channel_url_ytdlp(video_url)
    match = re.search(r"/channel/([^/]+)/?", url)
    if match:
        out: str = str(match.group(1))
        return ChannelId(out)
    raise RuntimeError(f"Could not find channel id in: {video_url} using yt-dlp.")


def fetch_videos_from_channel(channel_url: str) -> list[VideoId]:
    """Fetch the videos from a channel."""
    # yt-dlp -J "CHANNEL_URL" > channel_info.json
    # cmd = f'yt-dlp -i --get-id "https://www.youtube.com/channel/{channel_id}"'
    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe
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


def fetch_videos_from_youtube_channel(channel_id: str) -> list[VideoId]:
    """Fetch the videos from a youtube channel."""
    channel_url = f"https://www.youtube.com/channel/{channel_id}"
    return fetch_videos_from_channel(channel_url)
