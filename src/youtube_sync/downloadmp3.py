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
    """Download the youtube video as an mp3 using Docker."""
    import shutil
    import tempfile

    from youtube_sync.ytdlp import convert_audio_to_mp3, yt_dlp_download_best_audio

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Step 1: Download best audio
        result = yt_dlp_download_best_audio(
            url=url,
            temp_dir=temp_dir_path,
            cookies_txt=ytdlp.youtube_cookies_txt,
            no_geo_bypass=True,
        )

        if isinstance(result, Exception):
            raise result

        # Step 2: Convert to MP3
        temp_mp3 = Path(os.path.join(temp_dir, "converted.mp3"))
        mp3_result = convert_audio_to_mp3(result, temp_mp3)

        if isinstance(mp3_result, Exception):
            raise mp3_result

        # Step 3: Copy to final destination
        shutil.copy(str(temp_mp3), str(outmp3))


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
