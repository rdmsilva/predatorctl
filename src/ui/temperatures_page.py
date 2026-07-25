"""
predatorctl - ui/temperatures_page.py — CPU temperature history.

Package graph plus one sparkline per core (small multiples). Series accumulate
over time inside each sparkline; fixed Y scale (30–100 °C).
"""

from gi.repository import Gtk

from constants import temp_hex, MUTED
from ui.widgets import Sparkline, panel


class TemperaturesPage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.app = app
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._cores_built = False
        self._core_cells = []   # [(value_label, sparkline), ...]
        self._build_ui()

    def _build_ui(self):
        # ── Package (large graph) ─────────────────────────────
        pkg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pkg_value = Gtk.Label(label="--", xalign=0)
        self.pkg_value.add_css_class("gauge-value")
        pkg.append(self.pkg_value)
        self.pkg_spark = Sparkline(height=96)
        pkg.append(self.pkg_spark)
        self.append(panel("CPU · PACKAGE", pkg))

        # ── Cores (small multiples) ───────────────────────────
        self.cores_flow = Gtk.FlowBox()
        self.cores_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.cores_flow.set_homogeneous(True)
        self.cores_flow.set_min_children_per_line(2)
        self.cores_flow.set_max_children_per_line(6)
        self.cores_flow.set_column_spacing(10)
        self.cores_flow.set_row_spacing(10)
        self.append(panel("CORES", self.cores_flow))

        self.append(Gtk.Box(vexpand=True))

    def _build_cores(self, count):
        for i in range(count):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            cell.add_css_class("panel")
            cell.add_css_class("mini")

            header = Gtk.Box(spacing=6)
            name = Gtk.Label(label=f"CORE {i}", xalign=0, hexpand=True)
            name.add_css_class("metric-label")
            value = Gtk.Label(label="--", xalign=1)
            value.add_css_class("core-temp")
            header.append(name)
            header.append(value)

            spark = Sparkline(height=34)
            cell.append(header)
            cell.append(spark)

            self.cores_flow.append(cell)
            self._core_cells.append((value, spark))
        self._cores_built = True

    def refresh(self, data):
        cpu = data.cpu_temp
        if cpu is not None:
            self.pkg_value.set_markup(
                f"<span foreground='{temp_hex(cpu)}'>{cpu:.0f}°</span>")
            self.pkg_spark.push(cpu, temp_hex(cpu))
        else:
            self.pkg_value.set_label("N/A")

        cores = data.cpu_cores
        if cores and not self._cores_built:
            self._build_cores(len(cores))
        for i, t in enumerate(cores):
            if i >= len(self._core_cells):
                break
            value, spark = self._core_cells[i]
            value.set_markup(f"<span foreground='{temp_hex(t)}'>{t:.0f}°</span>")
            spark.push(t, temp_hex(t))
