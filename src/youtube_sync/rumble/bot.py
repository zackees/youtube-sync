# pylint: disable=R0801

import argparse
import os
import sys
from pathlib import Path

from youtube_sync.library import Library
from youtube_sync.rumble.rumble import (
    PartialVideo,
    fetch_rumble_channel_all_partial_result,
)
from youtube_sync.types import VidEntry


def _update_library(outdir: str, channel_name: str) -> Library:
    # channel_url = f"https://www.brighteon.com/channels/{channel_name}"
    library_json = os.path.join(outdir, "library.json")
    videos: list[PartialVideo] = fetch_rumble_channel_all_partial_result(
        channel_name=channel_name,
        channel=channel_name,
        after=None,
    )
    vids: list[VidEntry] = [
        VidEntry(url=vid.url, title=vid.title, date=vid.date) for vid in videos
    ]
    library_or_err = Library.from_json(Path(library_json))
    if isinstance(library_or_err, FileNotFoundError):
        raise FileNotFoundError(f"Library file not found: {library_json}")
    if isinstance(library_or_err, Exception):
        raise library_or_err
    library: Library = library_or_err
    library.merge(vids, save=True)
    return library


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--channel-name",
        type=str,
        help="URL slug of the channel, example: hrreport",
        required=True,
    )
    parser.add_argument("--output", type=str, help="Output directory", required=True)
    # full-scan
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading")
    args = parser.parse_args()
    outdir = args.output
    channel = args.channel_name

    library = _update_library(outdir, channel)
    print(f"Updated library {library.path}")
    if not args.skip_download:
        library.download_missing(download_limit=None, yt_dlp_uses_docker=False)
    return 0


def unit_test() -> int:
    """Run the tests."""
    sys.argv.append("--channel-name")
    sys.argv.append("PlandemicSeriesOfficial")
    sys.argv.append("--output")
    sys.argv.append("tmp")
    sys.argv.append("--skip-download")
    main()
    return 0


if __name__ == "__main__":
    sys.exit(unit_test())
