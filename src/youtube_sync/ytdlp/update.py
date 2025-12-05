"""
Download a youtube video as an mp3.
"""

import subprocess
import sys
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subprocess import CompletedProcess

# def download_mp3(url: str, outmp3: str, ytdlp: YtDlp) -> None:
#     """Download the youtube video as an mp3."""
#     return ytdlp.download_mp3(url=url, outmp3=outmp3)


def update_yt_dlp(check: bool) -> bool:
    from youtube_sync.ytdlp.exe import YtDlpCmdRunner

    yt_exe = YtDlpCmdRunner.create()
    if isinstance(yt_exe, Exception):
        warnings.warn(f"can't update because yt-dlp not found: {yt_exe}")
        return False
    # cmd_list = [yt_exe.exe.as_posix(), "--update"]
    cmd_list = ["--version"]
    cp: CompletedProcess[bytes] = yt_exe.run(cmd_list, check=False, capture_output=True)  # type: ignore[assignment]
    # cp = subprocess.run(cmd_list, check=False, capture_output=True)
    cps: list[CompletedProcess[bytes]] = [cp]
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
        cp = subprocess.run(cmd_list_pip_update, check=False, capture_output=True)  # type: ignore[misc]
        cps.append(cp)
        if cp.returncode != 0:
            stdout1: str = cps[0].stdout.decode("utf-8")
            stderr1: str = cps[0].stderr.decode("utf-8")
            stdout2: str = cps[1].stdout.decode("utf-8")
            stderr2: str = cps[1].stderr.decode("utf-8")
            msg = "Failed to update yt-dlp:\n"
            msg += f" first command:\n  {cps[0].args}\n  {stdout1}\n  {stderr1}\n"
            msg += f" second command:\n  {cps[1].args}\n  {stdout2}\n  {stderr2}\n"
            if check:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg)
    return cp.returncode == 0


# def unit_test() -> None:
#     """Run the tests."""

#     from youtube_sync import Source
#     from youtube_sync.uploader import FileUploader
#     from youtube_sync.ytdlp import YtDlp

#     url = "https://www.youtube.com/watch?v=3Zl9puhwiyw"
#     outmp3 = "tmp.mp3"
#     ytdlp = YtDlp(source=Source.YOUTUBE)
#     uploader = FileUploader()
#     ytdlp.download_mp3(url=url, outmp3=outmp3, uploader=uploader)
#     print(f"Downloaded {url} as {outmp3}")
#     os.remove(outmp3)


# if __name__ == "__main__":
#     unit_test()
