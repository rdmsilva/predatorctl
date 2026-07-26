"""
predatorctl - adapters/sysfs_sensors.py
READ adapter (driven adapter for SensorPort). Unprivileged.
Sources: linuwu_sense sysfs, /sys/firmware/acpi, /sys/class/power_supply,
plus scrapes of `sensors` (lm_sensors) and `nvidia-smi`.

Sensor chips are AUTO-DETECTED via `sensors -j` (JSON), by TYPE rather than
fixed address: CPU = coretemp (Intel) or k10temp/zenpower (AMD); NVMe = any
`nvme-*`; RAM = any `spd5118-*`/`jc42-*`; GPU = nvidia-smi, with a temperature
fallback to `amdgpu-*`. This makes it work on any Predator/Nitro running
linuwu_sense, not just the PHN16-72.

Every reader swallows errors and returns None/empty so the UI never breaks
when hardware or a command is missing.
"""

import subprocess
import json
from pathlib import Path

from domain.models import Telemetry, GpuInfo, Battery

LINUWU_BASE = Path("/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi")
PREDATOR_SENSE = LINUWU_BASE / "predator_sense"
FOUR_ZONED_KB = LINUWU_BASE / "four_zoned_kb"
PLATFORM_PROFILE = Path("/sys/firmware/acpi/platform_profile")
PROFILE_CHOICES = Path("/sys/firmware/acpi/platform_profile_choices")
POWER_SUPPLY = Path("/sys/class/power_supply")
RESTORE_CONF = Path("/etc/predatorctl/restore.conf")


def _read_sysfs(path):
    """Reads a sysfs file, returns string or None."""
    try:
        return path.read_text().strip()
    except (OSError, PermissionError):
        return None


class SensorAdapter:
    """Implements SensorPort. Instantiated by the composition root in main.py."""

    def __init__(self):
        self._bat_path = None   # detected on first read_battery()

    def read_fan_speed(self):
        """Returns (cpu, gpu) ints, or None when in auto mode."""
        val = _read_sysfs(PREDATOR_SENSE / "fan_speed")
        if val is None:
            return None
        if val == "0,0" or val == "0":
            return None  # auto
        parts = val.split(",")
        if len(parts) == 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except ValueError:
                return None
        return None

    def read_battery_limiter(self):
        """True when the 80% charge limit is active."""
        return _read_sysfs(PREDATOR_SENSE / "battery_limiter") == "1"

    def read_lcd_override(self):
        return _read_sysfs(PREDATOR_SENSE / "lcd_override") == "1"

    def read_on_ac(self):
        """True when the AC adapter ('Mains') is plugged in. Defaults True."""
        try:
            for supply in POWER_SUPPLY.iterdir():
                if _read_sysfs(supply / "type") == "Mains":
                    return _read_sysfs(supply / "online") == "1"
        except OSError:
            pass
        return True

    def read_platform_profile(self):
        return _read_sysfs(PLATFORM_PROFILE) or ""

    def read_platform_profile_choices(self):
        val = _read_sysfs(PROFILE_CHOICES)
        return val.split() if val else []

    def read_last_kb_effect(self):
        """Last four_zone_mode value predatorctl-helper saved for boot
        restore, or None. The RGB sysfs node has no read-back (see
        ui/rgb_page.py), so this file -- world-readable, root-owned -- is
        the only way to know what's actually configured on the keyboard."""
        text = _read_sysfs(RESTORE_CONF)
        if not text:
            return None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("four_zone_mode="):
                return line.partition("=")[2].strip()
        return None

    def _battery_path(self):
        """First 'Battery'-type supply (BAT0 on Nitro, BAT1 on PHN16-72…)."""
        if self._bat_path is None:
            try:
                for supply in sorted(POWER_SUPPLY.iterdir()):
                    if _read_sysfs(supply / "type") == "Battery":
                        self._bat_path = supply
                        break
            except OSError:
                pass
        return self._bat_path

    @staticmethod
    def _read_int(path):
        val = _read_sysfs(path)
        try:
            return int(val) if val else None
        except ValueError:
            return None

    def read_battery(self):
        """Reads battery status."""
        bat = Battery()
        base = self._battery_path()
        if base is None:
            return bat
        cap = self._read_int(base / "capacity")
        if cap is not None:
            bat.capacity = cap
        status = _read_sysfs(base / "status")
        if status:
            bat.status = status  # Charging/Discharging/Full
        volt = self._read_int(base / "voltage_now")
        if volt is not None:
            bat.voltage = round(volt / 1e6, 2)  # microvolts → volts
        curr = self._read_int(base / "current_now")
        if curr is not None:
            c = round(curr / 1e6, 2)  # microamps → amps
            bat.current = c
            if bat.voltage:
                bat.power = round(bat.voltage * c, 2)
        return bat

    # ── Sensors via `sensors -j` (auto-detection by chip TYPE) ─────────
    @staticmethod
    def _sensors_json():
        try:
            out = subprocess.check_output(
                ["sensors", "-j"], text=True, timeout=3, stderr=subprocess.DEVNULL
            )
            return json.loads(out)
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            return {}

    @staticmethod
    def _feat_temp(feature):
        """First `*_input` value inside a `sensors -j` feature dict."""
        if isinstance(feature, dict):
            for k, v in feature.items():
                if k.endswith("_input"):
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return None
        return None

    def _cpu_temp(self, s):
        """CPU package/Tctl: coretemp (Intel) or k10temp/zenpower (AMD)."""
        for chip, feats in s.items():
            low = chip.lower()
            if low.startswith("coretemp"):
                t = self._feat_temp(feats.get("Package id 0"))
                if t is not None:
                    return t
            elif low.startswith(("k10temp", "zenpower")):
                for key in ("Tctl", "Tdie", "Tccd1"):
                    t = self._feat_temp(feats.get(key))
                    if t is not None:
                        return t
        return None

    def _cpu_cores(self, s):
        """Per-core temperatures (Intel coretemp 'Core N')."""
        temps = []
        for chip, feats in s.items():
            if chip.lower().startswith("coretemp"):
                for name, feat in feats.items():
                    if name.startswith("Core "):
                        t = self._feat_temp(feat)
                        if t is not None:
                            temps.append(t)
        return temps

    def _nvme_temp(self, s):
        """Highest temperature among present NVMe drives (Composite or 1st sensor)."""
        best = None
        for chip, feats in s.items():
            if not chip.lower().startswith("nvme"):
                continue
            t = self._feat_temp(feats.get("Composite"))
            if t is None:
                for name, feat in feats.items():
                    if name != "Adapter":
                        t = self._feat_temp(feat)
                        if t is not None:
                            break
            if t is not None:
                best = t if best is None else max(best, t)
        return best

    def _ram_temp(self, s):
        """RAM temperature: any spd5118/jc42 chip."""
        for chip, feats in s.items():
            if chip.lower().startswith(("spd5118", "jc42")):
                for name, feat in feats.items():
                    if name != "Adapter":
                        t = self._feat_temp(feat)
                        if t is not None:
                            return t
        return None

    def read_gpu_info(self, s=None):
        """NVIDIA GPU via nvidia-smi; temperature fallback to amdgpu."""
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=temperature.gpu,utilization.gpu,power.draw,"
                    "clocks.current.sm,clocks.current.memory,fan.speed",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=3,
            ).strip()
            parts = [p.strip() for p in out.split(",")]
            return GpuInfo(
                temp=float(parts[0]) if parts[0] != "[N/A]" else None,
                usage=float(parts[1]) if parts[1] != "[N/A]" else None,
                power=float(parts[2]) if parts[2] != "[N/A]" else None,
                clock_sm=parts[3] if len(parts) > 3 else None,
                clock_mem=parts[4] if len(parts) > 4 else None,
                fan_speed=parts[5] if len(parts) > 5 and parts[5] != "[N/A]" else None,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        # AMD: temperature only, via sensors amdgpu-*
        for chip, feats in (s or {}).items():
            if chip.lower().startswith("amdgpu"):
                for key in ("edge", "junction", "temp1"):
                    t = self._feat_temp(feats.get(key))
                    if t is not None:
                        return GpuInfo(temp=t)
        return GpuInfo()

    def read_all(self) -> Telemetry:
        """Collects everything at once (called by the UI every 2s)."""
        s = self._sensors_json()   # runs `sensors` ONCE per cycle
        return Telemetry(
            cpu_temp=self._cpu_temp(s),
            cpu_cores=self._cpu_cores(s),
            gpu=self.read_gpu_info(s),
            nvme_temp=self._nvme_temp(s),
            ram_temp=self._ram_temp(s),
            fan_speed=self.read_fan_speed(),
            battery=self.read_battery(),
            battery_limiter=self.read_battery_limiter(),
            lcd_override=self.read_lcd_override(),
            platform_profile=self.read_platform_profile(),
            profile_choices=self.read_platform_profile_choices(),
            on_ac=self.read_on_ac(),
            kb_last_effect=self.read_last_kb_effect(),
        )
