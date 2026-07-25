"""Tests for the pure domain: constants (semantic colors) and models/ports."""

import unittest

import tests  # noqa: F401  (ensures src/ is on sys.path)

import constants
from domain.models import Telemetry, GpuInfo, Battery
from domain.ports import SensorPort, ControlPort
from adapters.sysfs_sensors import SensorAdapter
from adapters.pkexec_control import ControlAdapter


class TestTempSemantics(unittest.TestCase):
    def test_temp_class(self):
        self.assertEqual(constants.temp_class(None), "")
        self.assertEqual(constants.temp_class(30), "temp-cool")
        self.assertEqual(constants.temp_class(constants.T_WARM - 1), "temp-cool")
        self.assertEqual(constants.temp_class(constants.T_WARM), "temp-warm")
        self.assertEqual(constants.temp_class(constants.T_HOT - 1), "temp-warm")
        self.assertEqual(constants.temp_class(constants.T_HOT), "temp-hot")
        self.assertEqual(constants.temp_class(105), "temp-hot")

    def test_temp_hex(self):
        self.assertEqual(constants.temp_hex(None), constants.MUTED)
        self.assertEqual(constants.temp_hex(40), constants.COOL)
        self.assertEqual(constants.temp_hex(70), constants.WARM)
        self.assertEqual(constants.temp_hex(90), constants.HOT)

    def test_hex_rgb(self):
        self.assertEqual(constants._hex_rgb("#ffffff"), (1.0, 1.0, 1.0))
        self.assertEqual(constants._hex_rgb("000000"), (0.0, 0.0, 0.0))
        r, g, b = constants._hex_rgb("ff8000")
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(g, 128 / 255)
        self.assertAlmostEqual(b, 0.0)

    def test_temp_rgb_within_0_1(self):
        for t in (None, 20, 70, 95):
            for c in constants.temp_rgb(t):
                self.assertGreaterEqual(c, 0.0)
                self.assertLessEqual(c, 1.0)


class TestLookups(unittest.TestCase):
    def test_profile_map_covers_all_profiles(self):
        for p in ("low-power", "quiet", "balanced",
                  "balanced-performance", "performance"):
            self.assertIn(p, constants.PROFILE_MAP)

    def test_kb_effects_are_animated(self):
        # On the PHN16-72 static mode (0) doesn't light up — effects >= 1 only.
        for mode, _name in constants.KB_EFFECTS:
            self.assertGreaterEqual(mode, 1)
            self.assertLessEqual(mode, 7)

    def test_rgb_presets_valid_hex(self):
        for _name, hexval in constants.RGB_PRESETS:
            self.assertEqual(len(hexval), 6)
            int(hexval, 16)  # must not raise


class TestModels(unittest.TestCase):
    def test_telemetry_defaults_are_safe(self):
        """An empty Telemetry() (missing hardware) must never break the UI."""
        t = Telemetry()
        self.assertIsNone(t.cpu_temp)
        self.assertEqual(t.cpu_cores, [])
        self.assertIsInstance(t.gpu, GpuInfo)
        self.assertIsInstance(t.battery, Battery)
        self.assertIsNone(t.fan_speed)
        self.assertTrue(t.on_ac)

    def test_dataclass_instances_are_independent(self):
        a, b = Telemetry(), Telemetry()
        a.cpu_cores.append(50.0)
        self.assertEqual(b.cpu_cores, [])


class TestPorts(unittest.TestCase):
    def test_adapters_implement_the_ports(self):
        self.assertIsInstance(SensorAdapter(), SensorPort)
        self.assertIsInstance(ControlAdapter(), ControlPort)


if __name__ == "__main__":
    unittest.main()
