"""
predatorctl - domain/models.py
Domain data models. No GTK, sysfs or subprocess dependencies — the center of
the hexagonal architecture. Adapters convert raw hardware into these.
"""

from dataclasses import dataclass, field


@dataclass
class GpuInfo:
    temp: float | None = None
    usage: float | None = None
    power: float | None = None
    clock_sm: str | None = None
    clock_mem: str | None = None
    fan_speed: str | None = None


@dataclass
class Battery:
    capacity: int | None = None
    status: str | None = None        # Charging / Discharging / Full
    voltage: float | None = None
    current: float | None = None
    power: float | None = None


@dataclass
class Telemetry:
    """Full hardware snapshot, produced by SensorPort.read_all()."""
    cpu_temp: float | None = None
    cpu_cores: list[float] = field(default_factory=list)
    gpu: GpuInfo = field(default_factory=GpuInfo)
    nvme_temp: float | None = None
    ram_temp: float | None = None
    fan_speed: tuple[int, int] | None = None   # None = automatic (EC-controlled)
    battery: Battery = field(default_factory=Battery)
    battery_limiter: bool = False
    lcd_override: bool = False
    platform_profile: str = ""
    profile_choices: list[str] = field(default_factory=list)
    on_ac: bool = True   # AC adapter plugged in (Performance/Turbo require AC)
    kb_last_effect: str | None = None   # raw four_zone_mode last saved for boot restore
