"""predatorctl - ui/fan_page.py — fan control (instrumented readout + controls)."""

from gi.repository import Gtk, Adw

from constants import ACCENT
from ui.widgets import Gauge, panel


class FanPage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.app = app
        self._suppress_signal = False
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._build_ui()

    def _build_ui(self):
        # ── Current state (gauges) ────────────────────────────
        gauges = Gtk.Box(spacing=24, homogeneous=True)
        self.g_cpu = Gauge("CPU")
        self.g_gpu = Gauge("GPU")
        gauges.append(self.g_cpu)
        gauges.append(self.g_gpu)
        self.append(panel("FANS", gauges))

        # ── Control ───────────────────────────────────────────
        group = Adw.PreferencesGroup()
        self.auto_row = Adw.SwitchRow(
            title="Automatic Mode",
            subtitle="The EC controls the fans",
        )
        self.auto_row.connect("notify::active", self._on_auto_toggled)
        group.add(self.auto_row)

        self.cpu_row = Adw.SpinRow.new_with_range(0, 100, 5)
        self.cpu_row.set_title("CPU Fan (%)")
        self.cpu_row.connect("notify::value", self._on_slider_changed)
        group.add(self.cpu_row)

        self.gpu_row = Adw.SpinRow.new_with_range(0, 100, 5)
        self.gpu_row.set_title("GPU Fan (%)")
        self.gpu_row.connect("notify::value", self._on_slider_changed)
        group.add(self.gpu_row)
        self.append(panel("CONTROL", group))

        # ── Quick actions ─────────────────────────────────────
        btn_box = Gtk.Box(spacing=12)
        self.auto_btn = Gtk.Button(label="Back to Automatic")
        self.auto_btn.add_css_class("suggested-action")
        self.auto_btn.set_hexpand(True)
        self.auto_btn.connect("clicked", self._on_auto_btn_clicked)
        btn_box.append(self.auto_btn)

        max_btn = Gtk.Button(label="Maximum (100%)")
        max_btn.add_css_class("destructive-action")
        max_btn.set_hexpand(True)
        max_btn.connect("clicked", self._on_max_clicked)
        btn_box.append(max_btn)
        self.append(btn_box)

        self.append(Gtk.Box(vexpand=True))

    def refresh(self, data):
        fan = data.fan_speed
        self._suppress_signal = True
        if fan:
            self.auto_row.set_active(False)
            self.cpu_row.set_sensitive(True)
            self.gpu_row.set_sensitive(True)
            self.cpu_row.set_value(fan[0])
            self.gpu_row.set_value(fan[1])
            self.g_cpu.set_percent(fan[0], ACCENT)
            self.g_gpu.set_percent(fan[1], ACCENT)
        else:
            self.auto_row.set_active(True)
            self.cpu_row.set_sensitive(False)
            self.gpu_row.set_sensitive(False)
            self.g_cpu.set_text("AUTO")
            self.g_gpu.set_text("AUTO")
        self._suppress_signal = False

    def _on_auto_toggled(self, row, _):
        if self._suppress_signal:
            return
        auto = row.get_active()
        self.cpu_row.set_sensitive(not auto)
        self.gpu_row.set_sensitive(not auto)
        if auto:
            ok, msg = self.app.control.set_fan_auto()
            self.app.show_toast(msg)
        else:
            # Switching off auto must actually write manual values -- without
            # this, the sysfs fan_speed stays "0,0" (auto) and the next
            # refresh() tick reads that back and flips the switch on again.
            cpu = int(self.cpu_row.get_value())
            gpu = int(self.gpu_row.get_value())
            if cpu == 0 and gpu == 0:
                # "0,0" is itself the auto sentinel -- can't express manual
                # 0%/0%, so start manual mode from a safe non-zero value.
                cpu = gpu = 50
                self._suppress_signal = True
                self.cpu_row.set_value(cpu)
                self.gpu_row.set_value(gpu)
                self._suppress_signal = False
            ok, msg = self.app.control.set_fan_manual(cpu, gpu)
            self.g_cpu.set_percent(cpu, ACCENT)
            self.g_gpu.set_percent(gpu, ACCENT)
            self.app.show_toast(f"Fan: CPU {cpu}% / GPU {gpu}%" if ok else msg)

    def _on_slider_changed(self, *_):
        if self._suppress_signal:
            return
        if self.auto_row.get_active():
            return
        cpu = int(self.cpu_row.get_value())
        gpu = int(self.gpu_row.get_value())
        self.app.control.set_fan_manual(cpu, gpu)
        self.g_cpu.set_percent(cpu, ACCENT)
        self.g_gpu.set_percent(gpu, ACCENT)
        self.app.show_toast(f"Fan: CPU {cpu}% / GPU {gpu}%")

    def _on_auto_btn_clicked(self, _):
        self._suppress_signal = True
        self.auto_row.set_active(True)
        self.cpu_row.set_sensitive(False)
        self.gpu_row.set_sensitive(False)
        self._suppress_signal = False
        self.g_cpu.set_text("AUTO")
        self.g_gpu.set_text("AUTO")
        self.app.control.set_fan_auto()
        self.app.show_toast("Fan: AUTO (EC-controlled)")

    def _on_max_clicked(self, _):
        self._suppress_signal = True
        self.auto_row.set_active(False)
        self.cpu_row.set_value(100)
        self.gpu_row.set_value(100)
        self.cpu_row.set_sensitive(True)
        self.gpu_row.set_sensitive(True)
        self._suppress_signal = False
        self.g_cpu.set_percent(100, ACCENT)
        self.g_gpu.set_percent(100, ACCENT)
        self.app.control.set_fan_max()
        self.app.show_toast("Fans at MAXIMUM!")
