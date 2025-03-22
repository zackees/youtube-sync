import abc
import shutil
from pathlib import Path


class FileSystem(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def copy(self, src: Path, dest: str) -> None:
        pass


class RealFileSystem(FileSystem):
    def __init__(self) -> None:
        super().__init__()

    def copy(self, src: Path, dest: str) -> None:
        shutil.copy(str(src), dest)
