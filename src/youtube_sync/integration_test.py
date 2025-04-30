"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

from dataclasses import dataclass
from pathlib import Path

from youtube_sync import FSPath, RealFS, Source, YouTubeSync

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent
_TMP_DIR = PROJECT_ROOT / "tmp"
TMP_DIR = RealFS().get_path(_TMP_DIR.as_posix())

# def set_global_logging_level(level: int) -> None:
# set_global_logging_level("DEBUG")
# set_global_logging_level(logging.DEBUG)


@dataclass
class Args:
    """Command line arguments."""

    source: Source
    channel_name: str
    channel_id: str
    limit_scan: int
    skip_download: bool
    download_limit: int
    skip_scan: bool

    def get_out_path(self) -> FSPath:
        output = TMP_DIR / self.channel_name / "youtube"
        return output


def integration_test(args: Args) -> None:
    """Main function."""

    yt = YouTubeSync(
        channel_name=args.channel_name,
        channel_id=args.channel_id,
        media_output=args.get_out_path(),
        source=args.source,
    )

    if not args.skip_scan:
        vids = yt.scan_for_vids(args.limit_scan)
        if not vids:
            print("No new videos found.")
            raise SystemExit(1)

    if not args.skip_download:
        yt.download(args.download_limit)

    # print out the vids json file
    out = yt.library.to_json()
    import json

    json_str = json.dumps(out, indent=4)
    print(json_str)
    vid = out["vids"][0]
    upload_date = vid.get("date_upload")
    assert upload_date is not None
    print("Done")
