"""Tests for SensorAdapter: `sensors -j` parsers, fan_speed and battery.

Everything mocked — nothing here touches sysfs or actually runs subprocesses.
"""

import unittest
from pathlib import Path
from unittest import mock

import tests  # noqa: F401  (ensures src/ is on sys.path)

from adapters import sysfs_sensors
from adapters.sysfs_sensors import SensorAdapter

# Reduced `sensors -j` sample (Intel + dual NVMe + RAM + amdgpu)
SENSORS_INTEL = {
    "coretemp-isa-0000": {
        "Adapter": "ISA adapter",
        "Package id 0": {"temp1_input": 62.0},
        "Core 0": {"temp2_input": 55.0},
        "Core 1": {"temp3_input": 58.0},
    },
    "nvme-pci-0400": {
        "Adapter": "PCI adapter",
        "Composite": {"temp1_input": 41.9},
    },
    "nvme-pci-0500": {
        "Adapter": "PCI adapter",
        "Sensor 1": {"temp2_input": 48.0},   # no Composite → 1st sensor
    },
    "spd5118-i2c-0-51": {
        "Adapter": "SMBus adapter",
        "temp1": {"temp1_input": 39.8},
    },
}

SENSORS_AMD = {
    "k10temp-pci-00c3": {
        "Adapter": "PCI adapter",
        "Tctl": {"temp1_input": 71.5},
    },
    "amdgpu-pci-0300": {
        "Adapter": "PCI adapter",
        "edge": {"temp1_input": 64.0},
    },
}


class TestCpuParsers(unittest.TestCase):
    def setUp(self):
        self.ad = SensorAdapter()

    def test_cpu_intel_package(self):
        self.assertEqual(self.ad._cpu_temp(SENSORS_INTEL), 62.0)

    def test_cpu_amd_tctl(self):
        self.assertEqual(self.ad._cpu_temp(SENSORS_AMD), 71.5)

    def test_cpu_cores_intel(self):
        self.assertEqual(self.ad._cpu_cores(SENSORS_INTEL), [55.0, 58.0])

    def test_cpu_missing(self):
        self.assertIsNone(self.ad._cpu_temp({}))
        self.assertEqual(self.ad._cpu_cores({}), [])

    def test_feat_temp_invalid_input(self):
        self.assertIsNone(self.ad._feat_temp(None))
        self.assertIsNone(self.ad._feat_temp("text"))
        self.assertIsNone(self.ad._feat_temp({"temp1_input": "n/a"}))


class TestNvmeRam(unittest.TestCase):
    def setUp(self):
        self.ad = SensorAdapter()

    def test_nvme_takes_highest(self):
        # 41.9 (Composite) vs 48.0 (1st-sensor fallback) → 48.0
        self.assertEqual(self.ad._nvme_temp(SENSORS_INTEL), 48.0)

    def test_ram_spd5118(self):
        self.assertEqual(self.ad._ram_temp(SENSORS_INTEL), 39.8)

    def test_missing(self):
        self.assertIsNone(self.ad._nvme_temp(SENSORS_AMD))
        self.assertIsNone(self.ad._ram_temp(SENSORS_AMD))


class TestGpu(unittest.TestCase):
    def setUp(self):
        self.ad = SensorAdapter()

    def test_nvidia_smi_parse(self):
        out = "55, 12, 45.60, 1500, 8000, 30\n"
        with mock.patch.object(sysfs_sensors.subprocess, "check_output",
                               return_value=out):
            gpu = self.ad.read_gpu_info()
        self.assertEqual(gpu.temp, 55.0)
        self.assertEqual(gpu.usage, 12.0)
        self.assertEqual(gpu.power, 45.6)
        self.assertEqual(gpu.clock_sm, "1500")
        self.assertEqual(gpu.clock_mem, "8000")
        self.assertEqual(gpu.fan_speed, "30")

    def test_nvidia_smi_na(self):
        out = "[N/A], [N/A], [N/A], 0, 0, [N/A]\n"
        with mock.patch.object(sysfs_sensors.subprocess, "check_output",
                               return_value=out):
            gpu = self.ad.read_gpu_info()
        self.assertIsNone(gpu.temp)
        self.assertIsNone(gpu.fan_speed)

    def test_amdgpu_fallback(self):
        with mock.patch.object(sysfs_sensors.subprocess, "check_output",
                               side_effect=FileNotFoundError):
            gpu = self.ad.read_gpu_info(SENSORS_AMD)
        self.assertEqual(gpu.temp, 64.0)

    def test_no_gpu(self):
        with mock.patch.object(sysfs_sensors.subprocess, "check_output",
                               side_effect=FileNotFoundError):
            gpu = self.ad.read_gpu_info({})
        self.assertIsNone(gpu.temp)

    def test_sensors_json_failure_returns_empty_dict(self):
        with mock.patch.object(sysfs_sensors.subprocess, "check_output",
                               side_effect=FileNotFoundError):
            self.assertEqual(self.ad._sensors_json(), {})


class TestFanSpeed(unittest.TestCase):
    def setUp(self):
        self.ad = SensorAdapter()

    def _fan(self, raw):
        with mock.patch.object(sysfs_sensors, "_read_sysfs", return_value=raw):
            return self.ad.read_fan_speed()

    def test_auto(self):
        self.assertIsNone(self._fan("0,0"))
        self.assertIsNone(self._fan("0"))

    def test_manual(self):
        self.assertEqual(self._fan("50,70"), (50, 70))

    def test_missing_sysfs(self):
        self.assertIsNone(self._fan(None))

    def test_unexpected_value_does_not_crash(self):
        # Regression: an unguarded int() used to kill the whole refresh loop.
        self.assertIsNone(self._fan("a,b"))
        self.assertIsNone(self._fan("1,2,3"))


class TestBattery(unittest.TestCase):
    def setUp(self):
        self.ad = SensorAdapter()
        self.ad._bat_path = Path("/fake/BAT1")   # skip auto-detection

    def _battery(self, files):
        def fake_read(path):
            return files.get(path.name)
        with mock.patch.object(sysfs_sensors, "_read_sysfs",
                               side_effect=fake_read):
            return self.ad.read_battery()

    def test_full_readout(self):
        bat = self._battery({
            "capacity": "83",
            "status": "Discharging",
            "voltage_now": "15900000",
            "current_now": "1200000",
        })
        self.assertEqual(bat.capacity, 83)
        self.assertEqual(bat.status, "Discharging")
        self.assertEqual(bat.voltage, 15.9)
        self.assertEqual(bat.current, 1.2)
        self.assertEqual(bat.power, round(15.9 * 1.2, 2))

    def test_no_battery(self):
        self.ad._bat_path = None
        with mock.patch.object(sysfs_sensors, "_read_sysfs", return_value=None), \
             mock.patch.object(sysfs_sensors.Path, "iterdir", return_value=iter([])):
            bat = self.ad.read_battery()
        self.assertIsNone(bat.capacity)

    def test_corrupt_value_does_not_crash(self):
        bat = self._battery({"capacity": "??", "status": "Full"})
        self.assertIsNone(bat.capacity)
        self.assertEqual(bat.status, "Full")


if __name__ == "__main__":
    unittest.main()
