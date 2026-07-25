"""Tests for ControlAdapter: format/clamping of the values sent to the helper.

`_pkexec_write` is mocked — no pkexec is ever executed. What's tested is that
each setter produces EXACTLY the string the helper validates (the formats are
encoded independently on both sides and must match).
"""

import unittest
from unittest import mock

import tests  # noqa: F401  (ensures src/ is on sys.path)

from adapters import pkexec_control
from adapters.pkexec_control import ControlAdapter


class PkexecCaptureCase(unittest.TestCase):
    """Base: captures calls to _pkexec_write."""

    def setUp(self):
        self.ad = ControlAdapter()
        patcher = mock.patch.object(
            pkexec_control, "_pkexec_write", return_value=(True, "OK"))
        self.write = patcher.start()
        self.addCleanup(patcher.stop)


class TestFan(PkexecCaptureCase):
    def test_auto(self):
        self.ad.set_fan_auto()
        self.write.assert_called_once_with("fan_speed", "0,0")

    def test_manual(self):
        self.ad.set_fan_manual(50, 70)
        self.write.assert_called_once_with("fan_speed", "50,70")

    def test_manual_clamp(self):
        self.ad.set_fan_manual(-10, 250)
        self.write.assert_called_once_with("fan_speed", "0,100")

    def test_max(self):
        self.ad.set_fan_max()
        self.write.assert_called_once_with("fan_speed", "100,100")


class TestProfileToggles(PkexecCaptureCase):
    def test_profile(self):
        self.ad.set_platform_profile("balanced-performance")
        self.write.assert_called_once_with(
            "platform_profile", "balanced-performance")

    def test_battery_limiter(self):
        self.ad.set_battery_limiter(True)
        self.write.assert_called_with("battery_limiter", "1")
        self.ad.set_battery_limiter(False)
        self.write.assert_called_with("battery_limiter", "0")

    def test_lcd_override(self):
        self.ad.set_lcd_override(True)
        self.write.assert_called_with("lcd_override", "1")


class TestKeyboard(PkexecCaptureCase):
    def test_effect_format(self):
        # mode,speed,brightness,direction,R,G,B — R/G/B decimal
        self.ad.set_kb_effect(3, "#FF8000", brightness=80, speed=6, direction=2)
        self.write.assert_called_once_with("four_zone_mode", "3,6,80,2,255,128,0")

    def test_all_fields_clamped(self):
        self.ad.set_kb_effect(99, "ffffff", brightness=999, speed=99, direction=9)
        self.write.assert_called_once_with(
            "four_zone_mode", "7,9,100,2,255,255,255")

    def test_hex_without_hash(self):
        self.ad.set_kb_effect(1, "00ff00")
        self.write.assert_called_once_with("four_zone_mode", "1,4,100,1,0,255,0")

    def test_invalid_hex_does_not_call_pkexec(self):
        ok, msg = self.ad.set_kb_effect(1, "xyz")
        self.assertFalse(ok)
        self.assertIn("Invalid", msg)
        self.write.assert_not_called()

    def test_off(self):
        self.ad.set_kb_off()
        self.write.assert_called_once_with("four_zone_mode", "0,0,0,0,0,0,0")


class TestPkexecWrite(unittest.TestCase):
    """The real _pkexec_write, with subprocess mocked."""

    def _run(self, returncode=0, stdout="OK: x", stderr=""):
        proc = mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)
        with mock.patch.object(pkexec_control.subprocess, "run",
                               return_value=proc) as run:
            result = pkexec_control._pkexec_write("fan_speed", "0,0")
        return result, run

    def test_success(self):
        (ok, msg), run = self._run(0, "OK: fan_speed = 0,0")
        self.assertTrue(ok)
        self.assertEqual(msg, "OK: fan_speed = 0,0")
        # invoked DIRECTLY (pkexec <helper>), never via `pkexec python3 …`
        argv = run.call_args[0][0]
        self.assertEqual(argv[0], "pkexec")
        self.assertTrue(argv[1].endswith("helper/predatorctl-helper"))
        self.assertEqual(argv[2:], ["fan_speed", "0,0"])

    def test_failure(self):
        (ok, msg), _ = self._run(1, "", "ERROR: write failed")
        self.assertFalse(ok)
        self.assertEqual(msg, "ERROR: write failed")

    def test_pkexec_missing(self):
        with mock.patch.object(pkexec_control.subprocess, "run",
                               side_effect=FileNotFoundError):
            ok, msg = pkexec_control._pkexec_write("fan_speed", "0,0")
        self.assertFalse(ok)
        self.assertIn("pkexec", msg)


class TestHelperRoundTrip(unittest.TestCase):
    """Every string the adapter emits must pass the helper's validation."""

    @classmethod
    def setUpClass(cls):
        from tests.test_helper import helper
        cls.helper = helper

    def _emitted(self, call):
        ad = ControlAdapter()
        with mock.patch.object(pkexec_control, "_pkexec_write",
                               return_value=(True, "OK")) as w:
            call(ad)
        return w.call_args[0]

    def test_round_trip(self):
        cases = [
            lambda ad: ad.set_fan_auto(),
            lambda ad: ad.set_fan_manual(33, 66),
            lambda ad: ad.set_fan_max(),
            lambda ad: ad.set_platform_profile("performance"),
            lambda ad: ad.set_battery_limiter(True),
            lambda ad: ad.set_lcd_override(False),
            lambda ad: ad.set_kb_effect(2, "8000ff", brightness=55, speed=9),
            lambda ad: ad.set_kb_off(),
        ]
        for call in cases:
            action, value = self._emitted(call)
            self.assertTrue(self.helper.validate(action, value),
                            f"{action}={value!r} rejected by the helper")
            self.assertIn(action, self.helper.ACTIONS)


if __name__ == "__main__":
    unittest.main()
