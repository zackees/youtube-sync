"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

import argparse
from dataclasses import dataclass
from typing import Any

from youtube_sync import FSPath, RealFS, RemoteFS, Source, YouTubeSync


def _check_type(obj: Any, class_type: Any) -> None:
    """Check types."""
    if not isinstance(obj, class_type):
        raise TypeError(f"Expected {class_type}, got {type(obj)}")


@dataclass
class Args:
    """Command line arguments."""

    channel_name: str
    output: FSPath
    limit_scan: int
    skip_download: bool
    download_limit: int
    skip_scan: bool

    def __post_init__(self) -> None:
        # check types
        _check_type(self.channel_name, str)
        _check_type(self.output, FSPath)
        _check_type(self.limit_scan, int)
        _check_type(self.skip_download, bool)
        _check_type(self.download_limit, int)
        _check_type(self.skip_scan, bool)


def parse_args() -> Args:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser("youtube-sync")
    parser.add_argument(
        "--channel-name",
        type=str,
        # help="URL of the channel, example: https://www.youtube.com/@silverguru/videos",
        help="URL slug of the channel, example: @silverguru",
        required=True,
    )
    parser.add_argument("--output", type=str, help="Output directory", required=True)
    parser.add_argument(
        "--limit-scan",
        type=int,
        default=1000,
        help="Limit the number of the number of pages to scroll down",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the download of the videos.",
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        default=-1,
        help="Limit the number of videos to download",
    )
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Skip the update of the library.json file",
    )
    fs = RealFS()

    tmp = parser.parse_args()
    args = Args(
        channel_name=tmp.channel_name,
        output=FSPath(fs, tmp.output),
        limit_scan=tmp.limit_scan,
        skip_download=tmp.skip_download,
        download_limit=tmp.download_limit,
        skip_scan=tmp.skip_scan,
    )
    return args


def main() -> None:
    """Main function."""
    args = parse_args()
    yt = YouTubeSync(
        channel_name=args.channel_name,
        media_output=args.output,
        source=Source.YOUTUBE,
    )

    if not args.skip_scan:
        yt.scan_for_vids(args.limit_scan)

    if not args.skip_download:
        yt.download(args.download_limit)


def _get_test_dst_fsfile() -> FSPath:
    cwd = RealFS().cwd() / "tmp" / "@silverguru" / "youtube"
    return cwd


def _get_test_dst_fsfile_remote() -> FSPath:
    local_root = "dst:TorrentBooks/Transcriptions/test/silverguru/youtube"
    cwd = RemoteFS.from_rclone_config(src=local_root, rclone_conf=None).cwd()
    return cwd


def unit_test() -> None:
    """Unit test."""
    destination = _get_test_dst_fsfile()

    args = Args(
        channel_name="@silverguru",
        output=destination,
        limit_scan=1,
        skip_download=False,
        download_limit=1,
        skip_scan=False,
    )
    yt = YouTubeSync(
        channel_name=args.channel_name,
        media_output=args.output,
        source=Source.YOUTUBE,
    )
    yt.scan_for_vids(args.limit_scan)
    yt.download(args.download_limit)


if __name__ == "__main__":
    unit_test()
