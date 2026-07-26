"""Tests for predatorctl-restore: the boot-time preference restore script.

It never touches sysfs itself -- it only parses a config file and shells
out to predatorctl-helper, so these tests mock subprocess and exercise the
parsing/dispatch logic in isolation.
"""

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
RESTORE = ROOT / "helper" / "predatorctl-restore"


def _load_restore():
    """Imports the script (a file without the .py extension) as a module."""
    loader = importlib.machinery.SourceFileLoader("predatorctl_restore", str(RESTORE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


restore = _load_restore()


class TestParse(unittest.TestCase):
    def test_basic(self):
        text = "platform_profile=balanced\nbattery_limiter=1\n"
        self.assertEqual(
            list(restore.parse(text)),
            [("platform_profile", "balanced"), ("battery_limiter", "1")],
        )

    def test_blank_and_comment_lines_skipped(self):
        text = "\n# a comment\n   \nplatform_profile=quiet\n"
        self.assertEqual(list(restore.parse(text)), [("platform_profile", "quiet")])

    def test_whitespace_trimmed(self):
        text = "  platform_profile = balanced  \n"
        self.assertEqual(list(restore.parse(text)), [("platform_profile", "balanced")])

    def test_value_with_commas_preserved(self):
        text = "four_zone_mode=1,4,100,1,0,255,120\n"
        self.assertEqual(
            list(restore.parse(text)),
            [("four_zone_mode", "1,4,100,1,0,255,120")],
        )

    def test_line_without_equals_is_skipped_not_fatal(self):
        text = "platform_profile=balanced\ngarbage line\nbattery_limiter=0\n"
        self.assertEqual(
            list(restore.parse(text)),
            [("platform_profile", "balanced"), ("battery_limiter", "0")],
        )

    def test_empty_text(self):
        self.assertEqual(list(restore.parse("")), [])


class TestMain(unittest.TestCase):
    def test_no_config_file_is_a_noop(self):
        with patch.object(restore, "CONFIG", Path("/nonexistent/restore.conf")):
            self.assertEqual(restore.main(), 0)

    def test_calls_helper_once_per_line_with_helper_path(self):
        fake_config = MagicMock()
        fake_config.exists.return_value = True
        fake_config.read_text.return_value = (
            "platform_profile=balanced\nbattery_limiter=1\n"
        )
        completed = MagicMock(returncode=0, stdout="OK", stderr="")
        with patch.object(restore, "CONFIG", fake_config), \
             patch.object(restore, "subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = completed
            self.assertEqual(restore.main(), 0)

        self.assertEqual(mock_subprocess.run.call_count, 2)
        first_args = mock_subprocess.run.call_args_list[0][0][0]
        self.assertEqual(first_args, [str(restore.HELPER), "platform_profile", "balanced"])

    def test_a_failed_action_does_not_stop_the_rest(self):
        fake_config = MagicMock()
        fake_config.exists.return_value = True
        fake_config.read_text.return_value = (
            "platform_profile=bogus\nbattery_limiter=1\n"
        )
        results = [
            MagicMock(returncode=1, stdout="", stderr="ERROR: invalid value"),
            MagicMock(returncode=0, stdout="OK", stderr=""),
        ]
        with patch.object(restore, "CONFIG", fake_config), \
             patch.object(restore, "subprocess") as mock_subprocess:
            mock_subprocess.run.side_effect = results
            self.assertEqual(restore.main(), 1)

        self.assertEqual(mock_subprocess.run.call_count, 2)

    def test_helper_path_is_sibling_of_this_script(self):
        self.assertEqual(restore.HELPER.name, "predatorctl-helper")
        self.assertEqual(restore.HELPER.parent, RESTORE.parent)


if __name__ == "__main__":
    unittest.main()
