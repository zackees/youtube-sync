"""
Unit test file.
"""

import ast
import subprocess
import unittest
from pathlib import Path

from youtube_sync.ytdlp import yt_dlp_exe

HERE = Path(__file__).parent
TEST_DATA = HERE / "test_data" / "test_sync"


# --plugin-dirs


def _parse_plugin_dirs(stdout: str) -> list[Path]:
    """Parse plugin dirs."""
    lines = stdout.splitlines()
    for line in lines:
        if "Plugin directories" not in line:
            continue
        parts = line.split(":", maxsplit=1)
        # second part is the plugin dir value
        if len(parts) != 2:
            raise ValueError(f"Expected 2 parts, got {len(parts)}: {parts}")
        plugin_value = parts[1].strip()
        # this is now an array of string values like ['path1', 'path2']
        plugin_dirs = ast.literal_eval(plugin_value)
        # convert to Path
        return [Path(p) for p in plugin_dirs]
    raise ValueError(f"Could not find 'Plugin directories' in stdout: {stdout}")


def _get_plugin_dir() -> Path | Exception:
    """Get plugin directory."""
    exe = yt_dlp_exe()
    if exe is None:
        return FileNotFoundError("yt-dlp not found")

    try:
        cp = subprocess.run([exe, "--verbose"], capture_output=True)
        stdout_bytes = cp.stdout
        stderr_bytes = cp.stderr
        stdout = stdout_bytes.decode("utf-8") + stderr_bytes.decode("utf-8")
        assert (
            "yt-dlp" in stdout
        ), f"yt-dlp not in stdout: {stdout}, looks like an error"
        plugin_dirs = _parse_plugin_dirs(stdout)
        assert (
            len(plugin_dirs) > 0
        ), f"Expected at least one plugin dir, got {plugin_dirs}"
        return plugin_dirs[0]
    except Exception as e:
        import warnings

        warnings.warn(f"Failed to get plugin dir: {e}")
        return e


class YtDlpTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        exe = yt_dlp_exe()
        print(exe)
        print("done")

    def test_get_plugin_dir(self) -> None:
        plugin_dir = _get_plugin_dir()
        print(plugin_dir)
        print("done")


if __name__ == "__main__":
    unittest.main()
