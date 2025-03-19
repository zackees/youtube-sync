"""
Download a youtube video as an mp3.
"""

import os
import subprocess
import sys
import warnings
from pathlib import Path

from youtube_sync.ytdlp import YtDlp, yt_dlp_exe


def _add_ffmpeg_paths_once() -> None:
    from youtube_sync.ytdlp import add_ffmpeg_paths_once

    add_ffmpeg_paths_once()


def docker_yt_dlp_download_mp3(url: str, outmp3: Path, ytdlp: YtDlp) -> None:
    """Download the youtube video as an mp3."""
    raise NotImplementedError("docker_yt_dlp_download_mp3")
    # here = os.path.abspath(os.path.dirname(__file__))
    # dockerfile = os.path.join(here, "Dockerfile")
    # dockerfile = os.path.abspath(dockerfile)
    # assert os.path.exists(dockerfile), f"dockerfile {dockerfile} does not exist"
    # with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
    #     # cmd_args = [
    #     #     url,
    #     #     "-f",
    #     #     "bestaudio",
    #     #     "--extract-audio",
    #     #     "--audio-format",
    #     #     "mp3",
    #     #     "--output",
    #     #     "/host_dir/temp.mp3",
    #     #     "--update",
    #     #     "--no-geo-bypass",
    #     # ]
    #     cmd_args: list[str] = _get_ytdlp_command_mp3_download(
    #         yt_exe=Path("DELETE_THIS"),
    #         url=url,
    #         out_file=Path("/host_dir/temp.mp3"),
    #         update=True,
    #         no_geo_bypass=True,
    #         cookies_txt=ytdlp.youtube_cookies_txt,
    #     )
    #     # remove first element for docker cmd
    #     cmd_args.pop(0)
    #     docker_run(
    #         name="yt-dlp",
    #         dockerfile_or_url=dockerfile,
    #         cwd=Path(temp_dir),
    #         cmd_list=cmd_args,
    #     )
    #     shutil.copy(os.path.join(temp_dir, "temp.mp3"), str(outmp3))


def download_mp3(
    url: str, outmp3: Path, yt_dlp_uses_docker: bool, ytdlp: YtDlp
) -> None:
    """Download the youtube video as an mp3."""
    if yt_dlp_uses_docker:
        return docker_yt_dlp_download_mp3(url=url, outmp3=outmp3, ytdlp=ytdlp)
    return ytdlp.download_mp3(url=url, outmp3=outmp3)


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
