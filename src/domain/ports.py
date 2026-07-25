"""
predatorctl - domain/ports.py
Ports (interfaces) the adapters implement. The UI depends on these protocols,
never on the concrete adapters — that's what allows injecting a fake to test
off-hardware.

- SensorPort  : read port (unprivileged)
- ControlPort : write port (privileged, via pkexec)

Every write returns (success: bool, message: str) for the UI to show in a toast.
"""

from typing import Protocol, runtime_checkable

from domain.models import Telemetry

Result = tuple[bool, str]


@runtime_checkable
class SensorPort(Protocol):
    def read_all(self) -> Telemetry: ...


@runtime_checkable
class ControlPort(Protocol):
    def set_fan_auto(self) -> Result: ...
    def set_fan_manual(self, cpu_pct: int, gpu_pct: int) -> Result: ...
    def set_fan_max(self) -> Result: ...
    def set_platform_profile(self, profile: str) -> Result: ...
    def set_battery_limiter(self, enabled: bool) -> Result: ...
    def set_lcd_override(self, enabled: bool) -> Result: ...
    # Keyboard RGB: on the PHN16-72 only four_zone_mode (animated effects)
    # lights the backlight — per_zone_mode/static doesn't render.
    # See constants.KB_EFFECTS.
    def set_kb_effect(
        self, mode: int, color_hex: str, brightness: int = 100,
        speed: int = 4, direction: int = 1,
    ) -> Result: ...
    def set_kb_off(self) -> Result: ...
