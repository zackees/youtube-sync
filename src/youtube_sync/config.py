"""
Unit test file.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from virtual_fs import FSPath, Vfs

from youtube_sync import Source
from youtube_sync.json_util import load_dict
from youtube_sync.settings import ENV_JSON


@dataclass
class CmdOptions:
    download: bool
    scan: bool

    @staticmethod
    def from_dict(data: dict) -> "CmdOptions":
        download = data.get("download", True)
        scan = data.get("scan", True)
        return CmdOptions(
            download=download,
            scan=scan,
        )


@dataclass
class Channel:
    name: str
    source: Source
    channel_id: str

    @staticmethod
    def from_dict(data: dict) -> "Channel":
        return Channel(
            name=data["name"],
            source=Source.from_str(data["source"]),
            channel_id=data["channel_id"],
        )

    def to_fs_path(self, root: FSPath) -> FSPath:
        return root / self.name / self.source.value


class Config:
    """Represents the rclone configuration from the JSON file."""

    def __init__(
        self,
        output: str,
        rclone: dict,
        channels: list[Channel],
        cmd_options: CmdOptions,
    ):
        self.output = output
        self.rclone = rclone
        self.channels = channels
        self.cmd_options = cmd_options

    @staticmethod
    def from_dict(data: dict) -> "Config | Exception":
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
        cwd: FSPath = Vfs.begin(self.output, rclone_conf=self.rclone)
        # return [(channel, channel.to_fs_path(FSPath.from_str(self.output))) for channel in self.channels]
        return [(channel, channel.to_fs_path(cwd)) for channel in self.channels]
