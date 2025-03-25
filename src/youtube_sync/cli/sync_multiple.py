"""
Command entry point for syncing multiple YouTube channels.
"""

# pylint: disable=consider-using-f-string

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from virtual_fs import FSPath, Vfs

from youtube_sync import Channel, YouTubeSync
from youtube_sync.config import Config
from youtube_sync.logutil import create_logger
from youtube_sync.settings import ENV_JSON

logger = create_logger(__name__, logging.DEBUG)

# set debug
logging.basicConfig(level=logging.DEBUG)


def _check_type(obj: Any, class_type: Any) -> None:
    """Check types."""
    if not isinstance(obj, class_type):
        raise TypeError(f"Expected {class_type}, got {type(obj)}")


@dataclass
class Args:
    """Command line arguments."""

    config: Path | None
    dry_run: bool

    def __post_init__(self) -> None:
        # check types
        if isinstance(self.config, Path):
            _check_type(self.config, Path)
            assert self.config.exists()
            assert self.config.suffix == ".json"
        elif self.config is None:
            # Expect a json object in the environment
            if ENV_JSON not in os.environ:
                raise ValueError(
                    f"Expecting environment variable when config is None: {ENV_JSON}"
                )


def parse_args() -> Args:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser("youtube-sync-multiple")
    parser.add_argument(
        "config",
        type=Path,
        # help="URL of the channel, example: https://www.youtube.com/@silverguru/videos",
        help="Path to the json config file.",
        nargs="?",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run, do not download anything.",
    )
    tmp = parser.parse_args()
    config_path = Path(tmp.config)
    args = Args(config=config_path, dry_run=tmp.dry_run)
    return args


def _get_config(path: Path | None) -> Config | Exception:
    if path is not None:
        return Config.from_file(path)
    return Config.from_env()


def _process_channel(channel: Channel, cwd: FSPath, dry_run: bool) -> None:
    try:
        logger.info(f"Processing channel: {channel.name}")
        # Get source from channel
        source = channel.source
        path: FSPath = channel.to_fs_path(cwd)

        if dry_run:
            logger.info("Dry run, skipping download")
            logger.info(f"Channel: {channel.name}")
            logger.info(f"Output: {cwd}")
            logger.info(f"Source: {source}")
            logger.info(f"Path: {path}")
            return

        # Create YouTubeSync instance
        yt = YouTubeSync(
            channel_name=channel.name,
            media_output=path,
            source=source,
            channel_url=channel.channel_id,  # Using channel_id as the URL
        )

        # Default limits
        scan_limit = 1000  # Default value
        download_limit = None  # Default value

        # Scan for videos
        logger.info(f"Scanning channel {channel.name} with limit {scan_limit}")
        yt.scan_for_vids(scan_limit)

        # Download videos
        logger.info(
            f"Downloading videos for {channel.name} with limit {download_limit}"
        )
        yt.download(download_limit)

        logger.info(f"Finished processing channel: {channel.name}")
    except Exception as e:
        logger.error(f"Failed to process channel: {channel.name}")
        logger.error(e)


def run(args: Args) -> None:
    # Load the config file
    config = _get_config(args.config)
    if isinstance(config, Exception):
        logger.error(f"Failed to load config: {config}")
        raise config

    rclone_config = config.rclone

    output = config.output
    with Vfs.begin(output, rclone_conf=rclone_config) as cwd:
        # Process each channel in the config
        for channel in config.channels:
            _process_channel(channel=channel, cwd=cwd, dry_run=args.dry_run)


def main() -> None:
    args = parse_args()
    run(args)


def unit_test() -> None:
    """Unit test."""
    main()


if __name__ == "__main__":
    unit_test()
