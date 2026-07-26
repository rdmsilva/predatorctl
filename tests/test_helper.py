"""Tests for the privileged helper: ACTIONS whitelist + validate().

The helper is the project's security boundary — these tests guarantee the
validation rejects anything that isn't exactly the expected format.
"""

import importlib.machinery
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "helper" / "predatorctl-helper"


def _load_helper():
    """Imports the helper (a file without the .py extension) as a module."""
    loader = importlib.machinery.SourceFileLoader("predatorctl_helper", str(HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


helper = _load_helper()


class TestFanSpeed(unittest.TestCase):
    def test_auto(self):
        self.assertTrue(helper.validate("fan_speed", "0,0"))

    def test_valid_manual(self):
        for v in ("50,70", "0,100", "100,0", "1,1"):
            self.assertTrue(helper.validate("fan_speed", v), v)

    def test_out_of_range(self):
        for v in ("101,50", "50,101", "-1,50", "999,999"):
            self.assertFalse(helper.validate("fan_speed", v), v)

    def test_invalid_format(self):
        for v in ("", "50", "50,60,70", "a,b", "50;70", "50, 70",
                  " 50,70", "+5,70", "5_0,70", "50,70\n"):
            self.assertFalse(helper.validate("fan_speed", v), repr(v))

    def test_unicode_digits_rejected(self):
        # int("٥") == 5, but the raw value would go into sysfs — must be blocked.
        self.assertFalse(helper.validate("fan_speed", "٥٠,70"))


class TestToggles(unittest.TestCase):
    def test_toggles(self):
        for action in ("battery_limiter", "lcd_override", "backlight_timeout"):
            self.assertTrue(helper.validate(action, "0"), action)
            self.assertTrue(helper.validate(action, "1"), action)
            for v in ("2", "true", "on", "", "01", "-1"):
                self.assertFalse(helper.validate(action, v), f"{action}={v!r}")


class TestPlatformProfile(unittest.TestCase):
    def test_valid_profiles(self):
        for p in ("low-power", "quiet", "balanced",
                  "balanced-performance", "performance"):
            self.assertTrue(helper.validate("platform_profile", p), p)

    def test_invalid_profiles(self):
        for p in ("turbo", "Performance", "performance ", "", "eco"):
            self.assertFalse(helper.validate("platform_profile", p), repr(p))


class TestRgb(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(helper.validate("rgb", "ff0000,00ff00,0000ff,FFFFFF,100"))
        self.assertTrue(helper.validate("rgb", "000000,000000,000000,000000,0"))

    def test_invalid(self):
        for v in (
            "ff0000,00ff00,0000ff,ffffff",          # missing brightness
            "ff0000,00ff00,0000ff,ffffff,101",      # brightness > 100
            "ff0000,00ff00,0000ff,ffffff,100,x",    # extra field (was accepted!)
            "gg0000,00ff00,0000ff,ffffff,100",      # invalid hex
            "ff000,00ff00,0000ff,ffffff,100",       # 5 digits
            "+ff000,00ff00,0000ff,ffffff,100",      # sign
        ):
            self.assertFalse(helper.validate("rgb", v), v)


class TestFourZoneMode(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(helper.validate("four_zone_mode", "0,0,0,0,0,0,0"))
        self.assertTrue(helper.validate("four_zone_mode", "7,9,100,2,255,255,255"))
        self.assertTrue(helper.validate("four_zone_mode", "3,4,100,1,255,128,0"))

    def test_invalid(self):
        for v in (
            "8,0,0,0,0,0,0",          # mode > 7
            "0,10,0,0,0,0,0",         # speed > 9
            "0,0,101,0,0,0,0",        # brightness > 100
            "0,0,0,3,0,0,0",          # direction > 2
            "0,0,0,0,256,0,0",        # R > 255
            "0,0,0,0,0,0",            # 6 fields
            "0,0,0,0,0,0,0,0",        # 8 fields
            "a,0,0,0,0,0,0",
        ):
            self.assertFalse(helper.validate("four_zone_mode", v), v)


class TestWhitelist(unittest.TestCase):
    def test_unknown_action(self):
        self.assertFalse(helper.validate("shutdown", "now"))
        self.assertFalse(helper.validate("", ""))

    def test_every_action_has_validation(self):
        """No whitelisted action may accept arbitrary garbage."""
        for action in helper.ACTIONS:
            self.assertFalse(helper.validate(action, "../../etc/shadow"), action)
            self.assertFalse(helper.validate(action, "$(rm -rf /)"), action)

    def test_targets_are_sysfs_paths(self):
        """Every whitelisted target lives under /sys — never anywhere else."""
        for action, path in helper.ACTIONS.items():
            self.assertTrue(str(path).startswith("/sys/"), f"{action}: {path}")


class TestPersist(unittest.TestCase):
    """_persist() mirrors successful writes into restore.conf for the boot
    restore service -- exercised against a throwaway tmp dir, never the
    real /etc/predatorctl."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        restore_dir = Path(self.tmpdir.name) / "predatorctl"
        restore_conf = restore_dir / "restore.conf"
        patcher_dir = patch.object(helper, "RESTORE_DIR", restore_dir)
        patcher_conf = patch.object(helper, "RESTORE_CONF", restore_conf)
        patcher_dir.start()
        patcher_conf.start()
        self.addCleanup(patcher_dir.stop)
        self.addCleanup(patcher_conf.stop)
        self.restore_dir = restore_dir
        self.restore_conf = restore_conf

    def test_creates_dir_and_file_on_first_write(self):
        helper._persist("platform_profile", "balanced")
        self.assertTrue(self.restore_conf.exists())
        self.assertIn("platform_profile=balanced", self.restore_conf.read_text())

    def test_second_action_appends_first_is_kept(self):
        helper._persist("platform_profile", "balanced")
        helper._persist("battery_limiter", "1")
        text = self.restore_conf.read_text()
        self.assertIn("platform_profile=balanced", text)
        self.assertIn("battery_limiter=1", text)

    def test_same_action_updates_in_place_not_duplicated(self):
        helper._persist("platform_profile", "balanced")
        helper._persist("platform_profile", "performance")
        text = self.restore_conf.read_text()
        active_lines = [l for l in text.splitlines() if l.startswith("platform_profile=")]
        self.assertEqual(active_lines, ["platform_profile=performance"])

    def test_preserves_hand_edited_comments(self):
        self.restore_dir.mkdir(parents=True)
        self.restore_conf.write_text("# a hand-written note\n# fan_speed=0,0\n")
        helper._persist("platform_profile", "performance")
        text = self.restore_conf.read_text()
        self.assertIn("# a hand-written note", text)
        self.assertIn("# fan_speed=0,0", text)
        self.assertIn("platform_profile=performance", text)

    def test_oserror_does_not_raise(self):
        with patch.object(Path, "mkdir", side_effect=OSError("read-only filesystem")):
            helper._persist("platform_profile", "balanced")  # must not raise


class TestExecution(unittest.TestCase):
    def test_refuses_without_root(self):
        """Run as a regular user, the helper must refuse and exit 1."""
        proc = subprocess.run(
            [sys.executable, str(HELPER), "fan_speed", "0,0"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("must run as root", proc.stderr)


if __name__ == "__main__":
    unittest.main()
