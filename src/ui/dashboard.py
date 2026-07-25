"""predatorctl - ui/dashboard.py — instrument cluster (temperatures + telemetry)."""

from gi.repository import Gtk

from constants import PROFILE_MAP
from ui.widgets import Gauge, panel, metric


class DashboardPage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.app = app
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._build_ui()

    def _build_ui(self):
        # ── Temperature cluster ───────────────────────────────
        self.g_cpu = Gauge("CPU")
        self.g_gpu = Gauge("GPU")
        self.g_nvme = Gauge("NVME")
        self.g_ram = Gauge("RAM")

        gauges = Gtk.FlowBox()
        gauges.set_selection_mode(Gtk.SelectionMode.NONE)
        gauges.set_homogeneous(True)
        gauges.set_min_children_per_line(2)
        gauges.set_max_children_per_line(4)
        gauges.set_column_spacing(4)
        gauges.set_row_spacing(4)
        for g in (self.g_cpu, self.g_gpu, self.g_nvme, self.g_ram):
            gauges.append(g)

        self.append(panel("TEMPERATURES", gauges))

        # ── GPU (metrics) ─────────────────────────────────────
        gpu_row = Gtk.Box(spacing=8, homogeneous=True)
        self.m_gpu_use = metric(gpu_row, "USAGE")
        self.m_gpu_pwr = metric(gpu_row, "POWER")
        self.m_gpu_clk = metric(gpu_row, "CLOCK")
        self.m_gpu_fan = metric(gpu_row, "FAN")
        self.append(panel("GPU · DETAILS", gpu_row))

        # ── Fan + Profile ─────────────────────────────────────
        duo = Gtk.Box(spacing=16, homogeneous=True)
        fan_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.fan_value = Gtk.Label(label="--", xalign=0)
        self.fan_value.add_css_class("metric-value")
        fan_box.append(self.fan_value)
        duo.append(panel("FAN", fan_box))

        prof_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.prof_value = Gtk.Label(label="--", xalign=0)
        self.prof_value.add_css_class("metric-value")
        prof_box.append(self.prof_value)
        duo.append(panel("THERMAL PROFILE", prof_box))
        self.append(duo)

        self.append(Gtk.Box(vexpand=True))

    def refresh(self, data):
        self.g_cpu.set_temp(data.cpu_temp)
        self.g_gpu.set_temp(data.gpu.temp)
        self.g_nvme.set_temp(data.nvme_temp)
        self.g_ram.set_temp(data.ram_temp)

        gpu = data.gpu
        self.m_gpu_use.set_label(f"{gpu.usage:.0f}%" if gpu.usage is not None else "N/A")
        self.m_gpu_pwr.set_label(f"{gpu.power:.0f}W" if gpu.power is not None else "N/A")
        self.m_gpu_clk.set_label(f"{gpu.clock_sm}MHz" if gpu.clock_sm else "N/A")
        self.m_gpu_fan.set_label(f"{gpu.fan_speed}%" if gpu.fan_speed else "N/A")

        fan = data.fan_speed
        self.fan_value.set_label(f"CPU {fan[0]}% · GPU {fan[1]}%" if fan else "AUTO")

        prof = PROFILE_MAP.get(data.platform_profile)
        self.prof_value.set_label(prof[0] if prof else (data.platform_profile or "—"))
