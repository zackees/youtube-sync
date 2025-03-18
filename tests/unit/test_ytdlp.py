"""
Unit test file.
"""

import subprocess
import sys
import unittest
from pathlib import Path

from download import download

from youtube_sync.ytdlp import yt_dlp_exe, yt_dlp_plugin_dir

HERE = Path(__file__).parent
TEST_DATA = HERE / "test_data" / "test_sync"

CHROME_COOKIES_PLUGIN_ZIP = "https://github.com/zackees/youtube-sync/raw/refs/heads/main/yt-plugins/yt-dlp-ChromeCookieUnlock.zip"

# --plugin-dirs


def install_yt_dlp_plugin_from_url(
    zip_url: str,
    plugin_dir: Path | None = None,
    verbose: bool = False,
    reinstall: bool = False,
) -> Exception | None:
    """Install yt-dlp plugin."""

    def verbose_print(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    if plugin_dir is None:
        plugin_dir_or_err = yt_dlp_plugin_dir()
        if isinstance(plugin_dir_or_err, Exception):
            verbose_print(f"Error getting plugin dir: {plugin_dir_or_err}")
            return plugin_dir_or_err
        plugin_dir = plugin_dir_or_err
    assert isinstance(plugin_dir, Path)
    cache_dir = plugin_dir / "cache"
    zip_name = Path(zip_url).name
    download_dst = cache_dir / zip_name
    installed_breadcrump = (cache_dir / zip_name).with_suffix(".installed")
    if reinstall:
        if installed_breadcrump.exists():
            verbose_print(f"Removing installed breadcrump: {installed_breadcrump}")
            installed_breadcrump.unlink()
        if download_dst.exists():
            verbose_print(f"Removing download: {download_dst}")
            download_dst.unlink
    if installed_breadcrump.exists():
        verbose_print(f"Skipping install, already installed: {download_dst}")
        return None
    if download_dst.exists():
        verbose_print(f"Skipping download, already exists: {download_dst}")
    else:
        download(url=zip_url, path=download_dst, kind="file", replace=True)
    # lazy import to speed up the rest of the code
    from zipfile import ZipFile, ZipInfo

    with ZipFile(download_dst, "r") as zip_ref:
        # find the "yt_dlp_plugins" directory
        info: ZipInfo
        for info in zip_ref.infolist():
            is_file = not info.is_dir()
            filepath = Path(info.filename)
            if not is_file:
                verbose_print(f"Skipping directory: {filepath}")
                continue
            if "yt_dlp_plugins" not in filepath.parts:
                verbose_print(f"Skipping non-plugin file: {filepath}")
                continue
            verbose_print(f"Found plugin file: {filepath}")
            # extract the file
            relative_path = filepath.relative_to("yt_dlp_plugins")
            dst_path = plugin_dir / relative_path
            verbose_print(f"Extracting {filepath} -> {dst_path}")
            zip_ref.extract(info, plugin_dir.parent)
    verbose_print(f"Done installing plugin from {zip_url} to {plugin_dir}")
    installed_breadcrump.touch()
    verbose_print(f"Marking plugin installed via: {installed_breadcrump}")
    return None


def install_yt_dlp_win_plugin_chrome_cookies(verbose: bool = False) -> None:
    install_yt_dlp_plugin_from_url(CHROME_COOKIES_PLUGIN_ZIP, verbose=verbose)


def yt_dlp_install_plugins(verbose: bool = False) -> None:
    """Install yt-dlp plugins."""
    if sys.platform == "win32":
        install_yt_dlp_win_plugin_chrome_cookies(verbose=verbose)


def yt_dlp_verbose() -> str:
    """Get yt-dlp verbose output."""
    exe = yt_dlp_exe()
    cp = subprocess.run([exe, "--verbose"], capture_output=True)
    stdout_bytes = cp.stdout
    stderr_bytes = cp.stderr
    stdout = stdout_bytes.decode("utf-8") + stderr_bytes.decode("utf-8")
    return stdout


class YtDlpTester(unittest.TestCase):
    """Main tester class."""

    def test_simple(self) -> None:
        exe = yt_dlp_exe()
        print(exe)
        print("done")

    def test_get_plugin_dir(self) -> None:
        plugin_dir = yt_dlp_plugin_dir()
        print(plugin_dir)
        print("done")

    def test_install_plugin(self) -> None:
        yt_dlp_install_plugins(verbose=True)
        stdout = yt_dlp_verbose()
        print(stdout)
        print("done")


if __name__ == "__main__":
    unittest.main()
