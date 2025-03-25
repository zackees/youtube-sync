"""
Unit test file.
"""

import ast
import subprocess
from pathlib import Path

# _CHROME_COOKIES_PLUGIN_ZIP = "https://github.com/zackees/youtube-sync/raw/refs/heads/main/yt-plugins/yt-dlp-ChromeCookieUnlock.zip"


def _install_yt_dlp_plugin_from_url(
    zip_url: str,
    plugin_dir: Path | None = None,
    verbose: bool = False,
    reinstall: bool = False,
) -> Exception | None:
    """Install yt-dlp plugin."""
    from download import download

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


def yt_dlp_plugin_dir() -> Path | Exception:
    """Get plugin directory."""
    from youtube_sync.ytdlp.exe import YtDlpCmdRunner

    ytcmd: YtDlpCmdRunner | Exception = YtDlpCmdRunner.create(
        install_missing_plugins=False
    )

    if isinstance(ytcmd, Exception):
        return ytcmd

    exe = ytcmd.exe
    assert isinstance(exe, Path)

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


def yt_dlp_install_plugins(verbose: bool = False) -> dict[str, Exception] | None:
    """Install yt-dlp plugins."""
    # urls: list[str] = []
    # exceptions: dict[str, Exception] = {}
    # for url in urls:
    #     try:
    #         err = _install_yt_dlp_plugin_from_url(url, verbose=verbose)
    #         if err is not None:
    #             exceptions[url] = err
    #     except Exception as e:
    #         warnings.warn(f"Unexpected error installing plugin: {e}")
    #         exceptions[url] = e
    # if exceptions and verbose:
    #     print("One or more exceptions occurred:")
    #     for url, err in exceptions.items():
    #         print(f"URL: {url}, Error: {err}")
    # return exceptions if exceptions else None
    return None
