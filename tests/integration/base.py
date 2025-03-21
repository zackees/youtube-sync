"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from dataclasses import dataclass
from pathlib import Path

from youtube_sync import Source, YouTubeSync

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent
TMP_DIR = PROJECT_ROOT / "tmp"

# def set_global_logging_level(level: int) -> None:
# set_global_logging_level("DEBUG")
# set_global_logging_level(logging.DEBUG)


@dataclass
class Args:
    """Command line arguments."""

    source: Source
    channel_name: str
    limit_scroll_pages: int
    skip_download: bool
    download_limit: int
    skip_scan: bool
    yt_dlp_uses_docker: bool

    def get_out_path(self) -> Path:
        output = TMP_DIR / self.channel_name / "youtube"
        return output


def integration_test(args: Args) -> None:
    """Main function."""

    yt = YouTubeSync(
        channel_name=args.channel_name,
        media_output=args.get_out_path(),
        source=args.source,
        yt_dlp_uses_docker=args.yt_dlp_uses_docker,
    )

    if not args.skip_scan:
        vids = yt.scan_for_vids(args.limit_scroll_pages)
        if not vids:
            print("No new videos found.")
            raise SystemExit(1)

    if not args.skip_download:
        yt.download(args.download_limit)
