"""
Unit test file.
"""

import os
import tempfile
import unittest
from pathlib import Path

# COMMAND = "youtube-sync"
# --channel-name @CapitalCosm --output "E:\mikeadams\@CapitalCosm\youtube"

COMMAND = "youtube-sync --channel-name @CapitalCosm"  # --output E:\mikeadams\@CapitalCosm\youtube"


def _get_command(channel_name: str, output_dir: Path) -> str:
    return f"youtube-sync --channel-name {channel_name} --output {output_dir}"


class MainTester(unittest.TestCase):
    """Main tester class."""

    def test_imports(self) -> None:
        """Test command line interface (CLI)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            channel_name = "@CapitalCosm"
            command = _get_command(channel_name, output_dir) + " --help"
            print(f"Running command: {command}")
            rtn = os.system(command)
            self.assertEqual(0, rtn)


if __name__ == "__main__":
    unittest.main()
