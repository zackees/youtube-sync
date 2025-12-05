import shutil
import signal
import subprocess
import warnings
from pathlib import Path

from youtube_sync.ytdlp.error import set_keyboard_interrupt


def _yt_dlp_exe(install_missing_plugins: bool = True) -> Path | Exception:
    yt_exe = shutil.which("yt-dlp")
    if yt_exe is None:
        return FileNotFoundError("yt-dlp not found")
    if install_missing_plugins:
        from youtube_sync.ytdlp.plugins import yt_dlp_install_plugins

        errors: dict[str, Exception] | None = yt_dlp_install_plugins()
        if errors:
            warnings.warn(f"Failed to install yt-dlp plugins: {errors}")
    return Path(yt_exe)


def _is_keyboard_interrupt(rtn: int) -> bool:
    # if 3221225786 == rtn or rtn == -signal.SIGINT:
    if 3221225786 == rtn:
        return True
    if rtn == -signal.SIGINT:
        return True
    return False


class YtDlpCmdRunner:

    @staticmethod
    def is_keyboard_interrupt(rtn: int) -> bool:
        return _is_keyboard_interrupt(rtn)

    @staticmethod
    def create_or_raise(install_missing_plugins: bool = True) -> "YtDlpCmdRunner":
        yt_exe = _yt_dlp_exe(install_missing_plugins=install_missing_plugins)
        if isinstance(yt_exe, Exception):
            raise yt_exe
        return YtDlpCmdRunner(yt_exe)

    @staticmethod
    def create(install_missing_plugins: bool = True) -> "YtDlpCmdRunner | Exception":
        yt_exe = _yt_dlp_exe(install_missing_plugins=install_missing_plugins)
        if isinstance(yt_exe, Exception):
            return yt_exe
        return YtDlpCmdRunner(yt_exe)

    def __init__(self, exe: Path) -> None:
        self.exe = exe

    def run(self, args: list[str], **proc_args: object) -> subprocess.CompletedProcess[bytes]:  # type: ignore[reportUnknownParameterType]
        cmd_list = [self.exe.as_posix()] + args
        cmd_str = subprocess.list2cmdline(cmd_list)
        cp: subprocess.CompletedProcess[bytes] = subprocess.run(cmd_list, **proc_args)  # type: ignore[reportUnknownArgumentType]
        if cp.returncode != 0:  # type: ignore[reportUnknownMemberType]
            if _is_keyboard_interrupt(cp.returncode):  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                set_keyboard_interrupt()
                raise KeyboardInterrupt("KeyboardInterrupt")
            stdout = cp.stdout  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
            stderr = cp.stderr  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
            out: str = ""  # type: ignore[reportUnknownVariableType]
            if stdout:  # type: ignore[reportUnknownVariableType]
                if isinstance(stdout, bytes):
                    out += stdout.decode("utf-8")  # type: ignore[reportUnknownVariableType]
                else:
                    out += stdout  # type: ignore[reportUnknownVariableType]
            if stderr:  # type: ignore[reportUnknownVariableType]
                if isinstance(stderr, bytes):
                    out += stderr.decode("utf-8")  # type: ignore[reportUnknownVariableType]
                else:
                    out += stderr  # type: ignore[reportUnknownVariableType]
            msg = f"Failed to run yt-dlp with args: {cmd_str}\n  Return code: {cp.returncode}\n  out: {out}"  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            warnings.warn(msg)
            raise RuntimeError(msg)
        return cp  # type: ignore[reportUnknownVariableType]
