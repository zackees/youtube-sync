"""
Unit test file.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from virtual_fs import FSPath, Vfs

from youtube_sync.json_util import load_dict
from youtube_sync.logutil import create_logger
from youtube_sync.settings import ENV_JSON
from youtube_sync.types import Source

logger = create_logger(__name__, "WARNING")


@dataclass
class CmdOptions:
    download: bool
    scan: bool

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CmdOptions":
        download = data.get("download", True)
        scan = data.get("scan", True)
        return CmdOptions(
            download=download,
            scan=scan,
        )


def _youtube_fix_channel_id_if_necessary(channel_name: str) -> str:
    # youtube names must start with @
    if channel_name.startswith("@"):
        return channel_name
    logger.warning(f"Fixing youtube channel name: {channel_name} -> @{channel_name}")
    return f"@{channel_name}"


def _fix_channel_id_if_necessary(source: Source, channel_id: str) -> str:
    if source == Source.YOUTUBE:
        return _youtube_fix_channel_id_if_necessary(channel_id)
    return channel_id


@dataclass
class Channel:
    name: str
    source: Source
    channel_id: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Channel":
        return Channel(
            name=data["name"],
            source=Source.from_str(data["source"]),
            channel_id=data["channel_id"],
        )

    def to_fs_path(self, root: FSPath) -> FSPath:
        return root / self.name / self.source.value

    def __post_init__(self) -> None:
        assert isinstance(self.name, str), f"Expecting name to be a string: {self.name}"
        assert isinstance(
            self.source, Source
        ), f"Expecting source to be a Source: {self.source}"
        assert isinstance(
            self.channel_id, str
        ), f"Expecting channel_id to be a string: {self.channel_id}"
        self.channel_id = _fix_channel_id_if_necessary(self.source, self.channel_id)

    # hash
    def __hash__(self) -> int:
        return hash((self.name, self.source, self.channel_id))


def _remove_duplicates(channels: list[Channel]) -> list[Channel]:
    seen: set[Channel] = set()
    out: list[Channel] = []
    for channel in channels:
        if channel not in seen:
            out.append(channel)
            seen.add(channel)
        else:
            logger.warning(f"Duplicate channel: {channel} removed")
    return out


class Config:
    """Represents the rclone configuration from the JSON file."""

    def __init__(
        self,
        output: str,
        rclone: dict[str, Any],
        channels: list[Channel],
        cmd_options: CmdOptions,
    ):
        self.output = output
        self.rclone = rclone
        self.channels = _remove_duplicates(channels)
        self.cmd_options = cmd_options

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Config | Exception":
        try:
            channels = [Channel.from_dict(channel) for channel in data["channels"]]
            output = data["output"]
            rclone = data["rclone"]
            cmd_options = CmdOptions.from_dict(data.get("cmd_options", {}))
            out = Config(
                output=output,
                rclone=rclone,
                channels=channels,
                cmd_options=cmd_options,
            )
            return out
        except Exception as e:
            return e

    @staticmethod
    def from_file(json_path: Path) -> "Config | Exception":
        try:
            data = load_dict(json_path.read_text(encoding="utf-8"))
            return Config.from_dict(data)
        except Exception as e:
            return e

    @staticmethod
    def from_env() -> "Config | Exception":
        try:
            data_str = os.environ.get(ENV_JSON)
            assert data_str is not None, f"Expecting environment variable: {ENV_JSON}"
            data = load_dict(data_str)
            return Config.from_dict(data)
        except Exception as e:
            return e

    def to_paths(self) -> list[tuple[Channel, FSPath]]:
        cwd: FSPath = Vfs.begin(self.output, rclone_conf=self.rclone)  # type: ignore[reportUnknownMemberType]
        # return [(channel, channel.to_fs_path(FSPath.from_str(self.output))) for channel in self.channels]
        return [(channel, channel.to_fs_path(cwd)) for channel in self.channels]
