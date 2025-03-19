"""
Download a youtube video as an mp3.
"""

import _thread
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

from docker_run_cmd.api import docker_run
from static_ffmpeg import add_paths

from youtube_sync.ytdlp import YtDlp, yt_dlp_exe

FFMPEG_PATH_ADDED = False


def _add_ffmpeg_paths_once() -> None:
    global FFMPEG_PATH_ADDED  # pylint: disable=global-statement
    if not FFMPEG_PATH_ADDED:
        add_paths()
        FFMPEG_PATH_ADDED = True


def _get_ytdlp_command_mp3_download(
    yt_exe: Path,
    url: str,
    out_file: Path,
    update: bool,
    no_geo_bypass: bool,
    cookies_txt: Path | None,
) -> list[str]:
    _add_ffmpeg_paths_once()
    is_youtube = "youtube.com" in url or "youtu.be" in url
    if is_youtube:
        assert cookies_txt is not None, "cookies_txt must be provided for youtube.com"
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
        assert cookies_txt.exists(), f"cookies_txt does not exist: {cookies_txt}"
        cmd_list.append("--cookies")
        cmd_list.append(cookies_txt.as_posix())
    return cmd_list


def yt_dlp_download_mp3(url: str, outmp3: Path, ytdlp: YtDlp) -> None:
    """Download the youtube video as an mp3."""
    _add_ffmpeg_paths_once()
    par_dir = os.path.dirname(str(outmp3))
    if par_dir:
        os.makedirs(par_dir, exist_ok=True)

    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        raise yt_exe

    # yt_exe_str = yt_exe.as_posix()

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
                    cookies_txt=ytdlp.youtube_cookies_txt,
                )
                cmd_str = subprocess.list2cmdline(cmd_list)
                print(f"Running: {cmd_str}")
                subprocess.run(cmd_list, check=True)
                shutil.copy(temp_file, outmp3)
                return
            except KeyboardInterrupt:
                _thread.interrupt_main()
                raise
            except subprocess.CalledProcessError as cpe:
                print(f"Failed to download {url} as mp3: {cpe}")
                continue
        warnings.warn(f"Failed all attempts to download {url} as mp3.")


def docker_yt_dlp_download_mp3(url: str, outmp3: Path, ytdlp: YtDlp) -> None:
    """Download the youtube video as an mp3."""
    here = os.path.abspath(os.path.dirname(__file__))
    dockerfile = os.path.join(here, "Dockerfile")
    dockerfile = os.path.abspath(dockerfile)
    assert os.path.exists(dockerfile), f"dockerfile {dockerfile} does not exist"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        # cmd_args = [
        #     url,
        #     "-f",
        #     "bestaudio",
        #     "--extract-audio",
        #     "--audio-format",
        #     "mp3",
        #     "--output",
        #     "/host_dir/temp.mp3",
        #     "--update",
        #     "--no-geo-bypass",
        # ]
        cmd_args: list[str] = _get_ytdlp_command_mp3_download(
            yt_exe=Path("DELETE_THIS"),
            url=url,
            out_file=Path("/host_dir/temp.mp3"),
            update=True,
            no_geo_bypass=True,
            cookies_txt=ytdlp.youtube_cookies_txt,
        )
        # remove first element for docker cmd
        cmd_args.pop(0)
        docker_run(
            name="yt-dlp",
            dockerfile_or_url=dockerfile,
            cwd=Path(temp_dir),
            cmd_list=cmd_args,
        )
        shutil.copy(os.path.join(temp_dir, "temp.mp3"), str(outmp3))


def download_mp3(
    url: str, outmp3: Path, yt_dlp_uses_docker: bool, ytdlp: YtDlp
) -> None:
    """Download the youtube video as an mp3."""
    if yt_dlp_uses_docker:
        return docker_yt_dlp_download_mp3(url=url, outmp3=outmp3, ytdlp=ytdlp)
    return yt_dlp_download_mp3(url=url, outmp3=outmp3, ytdlp=ytdlp)


def update_yt_dlp(check: bool, yt_dlp_uses_docker: bool) -> bool:
    if yt_dlp_uses_docker:
        warnings.warn("yt-dlp-uses-docker is True. Cannot update yt-dlp.")
        return False
    yt_exe = yt_dlp_exe()
    if isinstance(yt_exe, Exception):
        warnings.warn(f"can't update because yt-dlp not found: {yt_exe}")
        return False
    cmd_list = [yt_exe.as_posix(), "--update"]
    cp = subprocess.run(cmd_list, check=False, capture_output=True)
    cps = [cp]
    if cp.returncode != 0:
        python_exe = sys.executable
        cmd_list_pip_update = [
            python_exe,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "yt-dlp",
        ]
        cp = subprocess.run(cmd_list_pip_update, check=False, capture_output=True)
        cps.append(cp)
        if cp.returncode != 0:
            stdout1 = cps[0].stdout.decode("utf-8")
            stderr1 = cps[0].stderr.decode("utf-8")
            stdout2 = cps[1].stdout.decode("utf-8")
            stderr2 = cps[1].stderr.decode("utf-8")
            msg = "Failed to update yt-dlp:\n"
            msg += f" first command:\n  {cps[0].args}\n  {stdout1}\n  {stderr1}\n"
            msg += f" second command:\n  {cps[1].args}\n  {stdout2}\n  {stderr2}\n"
            if check:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg)
    return cp.returncode == 0


def unit_test() -> None:
    """Run the tests."""
    url = "https://www.youtube.com/watch?v=3Zl9puhwiyw"
    outmp3 = Path("tmp.mp3")
    download_mp3(url=url, outmp3=outmp3, yt_dlp_uses_docker=False, ytdlp=YtDlp())
    print(f"Downloaded {url} as {outmp3}")
    os.remove(outmp3)


if __name__ == "__main__":
    unit_test()
