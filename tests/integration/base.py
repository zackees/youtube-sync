"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from dataclasses import dataclass
from pathlib import Path

from youtube_sync import Source, YouTubeSync


@dataclass
class Args:
    """Command line arguments."""

    source: Source
    channel_name: str
    output: Path
    limit_scroll_pages: int
    skip_download: bool
    download_limit: int
    skip_scan: bool
    yt_dlp_uses_docker: bool


def integration_test(args: Args) -> None:
    """Main function."""

    yt = YouTubeSync(
        channel_name=args.channel_name,
        media_output=args.output,
        source=args.source,
        yt_dlp_uses_docker=args.yt_dlp_uses_docker,
    )

    if not args.skip_scan:
        yt.scan_for_vids(args.limit_scroll_pages)

    if not args.skip_download:
        yt.download(args.download_limit)
