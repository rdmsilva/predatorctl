"""predatorctl - ui/battery_page.py — battery (instrumented readout) and protections."""

from gi.repository import Gtk, Adw

from constants import COOL, WARM, HOT, MUTED
from ui.widgets import Gauge, panel, metric


class BatteryPage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.app = app
        self._suppress = False
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._build_ui()

    def _build_ui(self):
        # ── Charge (gauge + metrics) ──────────────────────────
        row = Gtk.Box(spacing=24)
        self.gauge = Gauge("CHARGE")
        row.append(self.gauge)

        metrics = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                          valign=Gtk.Align.CENTER, hexpand=True)
        line = Gtk.Box(spacing=8, homogeneous=True)
        self.m_status = metric(line, "STATUS")
        self.m_power = metric(line, "POWER")
        self.m_volt = metric(line, "VOLTAGE")
        metrics.append(line)
        row.append(metrics)

        self.append(panel("BATTERY", row))

        # ── Protection (libadwaita toggles, already themed) ───
        group = Adw.PreferencesGroup()
        self.limiter_row = Adw.SwitchRow(
            title="Limit Charge to 80%",
            subtitle="Preserves battery lifespan",
        )
        self.limiter_row.connect("notify::active", self._on_limiter_toggled)
        group.add(self.limiter_row)

        self.lcd_row = Adw.SwitchRow(
            title="LCD Override",
            subtitle="Reduces display ghosting",
        )
        self.lcd_row.connect("notify::active", self._on_lcd_toggled)
        group.add(self.lcd_row)
        self.append(panel("PROTECTION", group))

        self.append(Gtk.Box(vexpand=True))

    @staticmethod
    def _charge_color(pct):
        if pct is None:
            return MUTED
        if pct >= 50:
            return COOL
        if pct >= 20:
            return WARM
        return HOT

    def refresh(self, data):
        bat = data.battery
        self.gauge.set_percent(bat.capacity, self._charge_color(bat.capacity))
        self.m_status.set_label(bat.status or "—")
        self.m_power.set_label(f"{bat.power:.1f}W" if bat.power is not None else "—")
        self.m_volt.set_label(f"{bat.voltage:.2f}V" if bat.voltage is not None else "—")

        self._suppress = True
        self.limiter_row.set_active(data.battery_limiter)
        self.lcd_row.set_active(data.lcd_override)
        self._suppress = False

    def _on_limiter_toggled(self, row, _):
        if self._suppress:
            return
        ok, msg = self.app.control.set_battery_limiter(row.get_active())
        self.app.show_toast(msg)

    def _on_lcd_toggled(self, row, _):
        if self._suppress:
            return
        ok, msg = self.app.control.set_lcd_override(row.get_active())
        self.app.show_toast(msg)
