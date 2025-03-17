"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from youtube_sync import Source, YouTubeSync


def _check_type(obj: Any, class_type: Any) -> None:
    """Check types."""
    if not isinstance(obj, class_type):
        raise TypeError(f"Expected {class_type}, got {type(obj)}")


@dataclass
class Args:
    """Command line arguments."""

    channel_name: str
    output: Path
    limit_scroll_pages: int
    skip_download: bool
    download_limit: int
    skip_scan: bool
    yt_dlp_uses_docker: bool

    def __post_init__(self) -> None:
        # check types
        _check_type(self.channel_name, str)
        _check_type(self.output, Path)
        _check_type(self.limit_scroll_pages, int)
        _check_type(self.skip_download, bool)
        _check_type(self.download_limit, int)
        _check_type(self.skip_scan, bool)
        _check_type(self.yt_dlp_uses_docker, bool)


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
        "--limit-scroll-pages",
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
    parser.add_argument(
        "--yt-dlp-uses-docker",
        action="store_true",
        help="Use docker to run yt-dlp",
    )
    tmp = parser.parse_args()
    args = Args(
        channel_name=tmp.channel_name,
        output=Path(tmp.output),
        limit_scroll_pages=tmp.limit_scroll_pages,
        skip_download=tmp.skip_download,
        download_limit=tmp.download_limit,
        skip_scan=tmp.skip_scan,
        yt_dlp_uses_docker=tmp.yt_dlp_uses_docker,
    )
    return args


def main() -> None:
    """Main function."""
    args = parse_args()
    # youtube_sync(
    #     channel_name=args.channel_name,
    #     media_output=args.output,
    #     limit_scroll_pages=args.limit_scroll_pages,
    #     download=not args.skip_download,
    #     download_limit=args.download_limit,
    #     scan=not args.skip_scan,
    #     yt_dlp_uses_docker=args.yt_dlp_uses_docker,
    # )
    yt = YouTubeSync(
        channel_name=args.channel_name,
        media_output=args.output,
        source=Source.YOUTUBE,
        # limit_scroll_pages=args.limit_scroll_pages,
        # download=not args.skip_download,
        # download_limit=args.download_limit,
        # scan=not args.skip_scan,
        yt_dlp_uses_docker=args.yt_dlp_uses_docker,
    )

    if not args.skip_scan:
        yt.scan_for_vids(args.limit_scroll_pages)

    if not args.skip_download:
        yt.download(args.download_limit)


if __name__ == "__main__":
    import sys

    sys.argv.append("--channel-name")
    sys.argv.append("@silverguru")
    sys.argv.append("--output")
    sys.argv.append(os.path.join(os.getcwd(), "tmp", "@silverguru", "youtube"))
    sys.argv.append("--limit-scroll-pages")
    sys.argv.append("1")
    sys.argv.append("--download-limit")
    sys.argv.append("1")
    main()
