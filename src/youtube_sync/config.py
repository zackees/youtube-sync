"""
Unit test file.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from virtual_fs import FSPath, Vfs

from youtube_sync import Source
from youtube_sync.json_util import load_dict


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

    def __init__(self, output: str, rclone: dict, channels: list[Channel]):
        self.output = output
        self.rclone = rclone
        self.channels = channels

    @staticmethod
    def from_dict(data: dict) -> "Config | Exception":
        try:
            channels = [Channel.from_dict(channel) for channel in data["channels"]]
            out = Config(
                output=data["output"], rclone=data["rclone"], channels=channels
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
            data_str = os.environ.get("RCLONE_CONFIG_JSON")
            assert (
                data_str is not None
            ), "Expecting environment variable: RCLONE_CONFIG_JSON"
            data = load_dict(data_str)
            return Config.from_dict(data)
        except Exception as e:
            return e

    def to_paths(self) -> list[tuple[Channel, FSPath]]:
        cwd: FSPath = Vfs.begin(self.output, rclone_conf=self.rclone)
        # return [(channel, channel.to_fs_path(FSPath.from_str(self.output))) for channel in self.channels]
        return [(channel, channel.to_fs_path(cwd)) for channel in self.channels]
