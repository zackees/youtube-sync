import abc
import shutil
from pathlib import Path


class FileSystem(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def copy(self, src: Path | str, dest: Path | str) -> None:
        pass

    @abc.abstractmethod
    def read_binary(self, path: Path | str) -> bytes:
        pass

    @abc.abstractmethod
    def exists(self, path: Path | str) -> bool:
        pass

    def read_text(self, path: Path | str) -> str:
        utf = self.read_binary(path)
        return utf.decode("utf-8")


class RealFileSystem(FileSystem):
    def __init__(self) -> None:
        super().__init__()

    def copy(self, src: Path | str, dest: Path | str) -> None:
        shutil.copy(str(src), str(dest))

    def read_binary(self, path: Path | str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def exists(self, path: Path | str) -> bool:
        return Path(path).exists()


class FSPath:
    def __init__(self, fs: FileSystem, path: str) -> None:
        self.path = path
        self.fs = fs

    def read_text(self) -> str:
        return self.fs.read_text(self.path)

    def read_binary(self) -> bytes:
        return self.fs.read_binary(self.path)

    def exists(self) -> bool:
        return self.fs.exists(self.path)
