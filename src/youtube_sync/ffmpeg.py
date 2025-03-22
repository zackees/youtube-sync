import _thread
import signal
import subprocess
import time
from pathlib import Path

from static_ffmpeg import add_paths

from youtube_sync.ytdlp.error import (
    KeyboardInterruptException,
    check_keyboard_interrupt,
    set_keyboard_interrupt,
)

_FFMPEG_PATH_ADDED = False


def init_once() -> None:
    global _FFMPEG_PATH_ADDED  # pylint: disable=global-statement
    if not _FFMPEG_PATH_ADDED:
        add_paths()
        _FFMPEG_PATH_ADDED = True


def convert_audio_to_mp3(input_file: Path, output_file: Path) -> Path | Exception:
    """Convert audio file to MP3 format using ffmpeg.

    Args:
        input_file: Path to the input audio file
        output_file: Path to save the output MP3 file

    Returns:
        Path to the output MP3 file or Exception if conversion failed
    """
    if check_keyboard_interrupt():
        return KeyboardInterruptException(
            "Conversion aborted due to previous keyboard interrupt"
        )

    init_once()

    # Ensure the output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd_list = [
        "ffmpeg",
        "-i",
        str(input_file),
        "-codec:a",
        "libmp3lame",
        "-qscale:a",
        "2",  # High quality setting
        "-y",  # Overwrite output file if it exists
        str(output_file),
    ]

    try:
        print(f"Begin {input_file} -> {output_file}")
        # proc = subprocess.Popen(cmd_list)
        # pipe to devnull to suppress output
        proc = subprocess.Popen(
            cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Monitor the process and check for interrupts
        while proc.poll() is None:
            if check_keyboard_interrupt():
                proc.terminate()
                return KeyboardInterruptException(
                    "Conversion aborted due to previous keyboard interrupt"
                )
            time.sleep(0.1)

        if proc.returncode != 0:
            rtn = proc.returncode
            if 3221225786 == rtn or rtn == -signal.SIGINT:
                set_keyboard_interrupt()
                raise KeyboardInterrupt("KeyboardInterrupt")

            return subprocess.CalledProcessError(proc.returncode, cmd_list)
        print(f"Conversion successful: {input_file} -> {output_file}")
        return output_file
    except KeyboardInterrupt:
        set_keyboard_interrupt()
        _thread.interrupt_main()
        raise
    except subprocess.CalledProcessError as e:
        return e
