"""
predatorctl - adapters/pkexec_control.py
WRITE adapter (driven adapter for ControlPort). Privileged.

The project's single privilege surface: every write goes through
`pkexec <helper>/predatorctl-helper <action> <value>`, which authenticates
via polkit and validates against a whitelist before writing to sysfs.
Arguments go on the command line, NOT stdin (pkexec does not forward stdin).

Do not add privileged paths outside this helper — see CLAUDE.md.
"""

import subprocess
from pathlib import Path

# adapters/ -> src/ -> project root; the helper lives in <root>/helper/
HELPER = str(Path(__file__).resolve().parents[2] / "helper" / "predatorctl-helper")


def _pkexec_write(action, value):
    """
    Performs a write via pkexec. Returns (success: bool, message: str).
    The helper is invoked DIRECTLY (not via `python3 helper`) so the polkit
    rule can match it by program path (auth_admin_keep). Requires the helper
    to be +x with a shebang — guaranteed by install.sh (and in the repo for
    running from source).
    """
    try:
        result = subprocess.run(
            ["pkexec", HELPER, action, str(value)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "OK"
        return False, result.stderr.strip() or f"Error (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, "Timeout — password not confirmed?"
    except FileNotFoundError:
        return False, "pkexec not found"
    except Exception as e:
        return False, str(e)


class ControlAdapter:
    """Implements ControlPort. Instantiated by the composition root in main.py."""

    def set_fan_auto(self):
        return _pkexec_write("fan_speed", "0,0")

    def set_fan_manual(self, cpu_pct, gpu_pct):
        cpu_pct = max(0, min(100, int(cpu_pct)))
        gpu_pct = max(0, min(100, int(gpu_pct)))
        return _pkexec_write("fan_speed", f"{cpu_pct},{gpu_pct}")

    def set_fan_max(self):
        return _pkexec_write("fan_speed", "100,100")

    def set_platform_profile(self, profile):
        """profile: low-power, quiet, balanced, balanced-performance, performance"""
        return _pkexec_write("platform_profile", profile)

    def set_battery_limiter(self, enabled):
        return _pkexec_write("battery_limiter", "1" if enabled else "0")

    def set_lcd_override(self, enabled):
        return _pkexec_write("lcd_override", "1" if enabled else "0")

    def set_kb_effect(self, mode, color_hex, brightness=100, speed=4, direction=1):
        """
        Keyboard RGB effect via four_zone_mode.
        Format: mode,speed,brightness,direction,R,G,B (R/G/B decimal 0-255).

        On the PHN16-72 only the animated effects (mode >= 1: breathing, neon,
        wave…) light the keyboard; static mode (0) and per_zone_mode don't
        render.
        """
        color_hex = color_hex.lstrip("#")
        try:
            if len(color_hex) != 6:
                raise ValueError
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
        except ValueError:
            return False, f"Invalid color: '{color_hex}' (use RRGGBB)"
        mode = max(0, min(7, int(mode)))
        speed = max(0, min(9, int(speed)))
        brightness = max(0, min(100, int(brightness)))
        direction = max(0, min(2, int(direction)))
        value = f"{mode},{speed},{brightness},{direction},{r},{g},{b}"
        return _pkexec_write("four_zone_mode", value)

    def set_kb_off(self):
        """Turns the backlight off (static black, brightness 0)."""
        return _pkexec_write("four_zone_mode", "0,0,0,0,0,0,0")
