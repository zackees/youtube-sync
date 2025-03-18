"""
An experimental python api use, but doesn't work with docker.
"""

import json
from pathlib import Path

import yt_dlp

URL = "https://www.youtube.com/watch?v=XfELJU1mRMg"


def yt_dlp_vid_info(url: str) -> dict | Exception:
    print("\n\n\n\n")
    ydl_opts: dict = {
        "verbose": True,
        "--cookies-from-browser": ("chrome",),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            ydl.print_debug_header()
            print("done")
        except yt_dlp.utils.DownloadError as e:
            return e
    if not isinstance(info, dict):
        return Exception(f"Expected dict, got {type(info)}")
    return info


def print_info(url: str) -> None:
    # ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
    # ydl_opts = {}
    # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #     info = ydl.extract_info(url, download=False)

    #     # ℹ️ ydl.sanitize_info makes the info json-serializable
    #     print(json.dumps(ydl.sanitize_info(info)))

    info_or_err = yt_dlp_vid_info(url)
    if isinstance(info_or_err, Exception):
        raise info_or_err
    info = info_or_err
    print(json.dumps(info, indent=2))


def yt_dlp_download_audio(url: str, out_audio: Path) -> None:
    assert out_audio.suffix in [".mp3", ".m4a"]
    suffix = out_audio.suffix.replace(".", "")
    # out_audio_no_suffix = out_audio.with_suffix('')
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": suffix,
                "preferredquality": "192",
            }
        ],
        "outtmpl": str(out_audio),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


print_info(URL)
# yt_dlp_download_audio(URL, Path("test.m4a"))
