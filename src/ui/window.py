"""predatorctl - ui/window.py — main window with lateral sidebar and refresh loop."""

import os
import threading

from gi.repository import Gtk, Adw, GLib

from constants import APP_NAME, ACCENT, TEXT, PROFILE_MAP
from ui.dashboard import DashboardPage
from ui.temperatures_page import TemperaturesPage
from ui.fan_page import FanPage
from ui.profile_page import ProfilePage
from ui.rgb_page import RgbPage
from ui.battery_page import BatteryPage


class PredatorWindow(Adw.ApplicationWindow):
    # (id, title, symbolic icon)
    NAV = [
        ("dashboard", "Dashboard", "view-grid-symbolic"),
        ("temperatures", "Temperatures", "office-chart-line-symbolic"),
        ("fan", "Fan", "speedometer-symbolic"),
        ("profile", "Profile", "preferences-system-symbolic"),
        ("rgb", "RGB", "input-keyboard-symbolic"),
        ("battery", "Battery", "battery-good-symbolic"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_css_class("instrument")
        self.set_title(APP_NAME)
        self.set_default_size(940, 720)

        self._refresh_lock = False

        # Pages
        self.dashboard_page = DashboardPage(self.app_ref)
        self.temperatures_page = TemperaturesPage(self.app_ref)
        self.fan_page = FanPage(self.app_ref)
        self.profile_page = ProfilePage(self.app_ref)
        self.rgb_page = RgbPage(self.app_ref)
        self.battery_page = BatteryPage(self.app_ref)
        self._pages = {
            "dashboard": self.dashboard_page,
            "temperatures": self.temperatures_page,
            "fan": self.fan_page,
            "profile": self.profile_page,
            "rgb": self.rgb_page,
            "battery": self.battery_page,
        }

        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(212)
        split.set_max_sidebar_width(240)
        split.set_sidebar(self._build_sidebar())
        split.set_content(self._build_content())
        self.set_content(split)

        # Initial selection (PREDATOR_PAGE opens straight on a given tab)
        try:
            initial = int(os.environ.get("PREDATOR_PAGE", "0"))
        except ValueError:
            initial = 0
        initial = max(0, min(len(self.NAV) - 1, initial))
        self.nav_list.select_row(self.nav_list.get_row_at_index(initial))

        # Auto-refresh
        GLib.timeout_add_seconds(2, self._tick)
        self._tick()

    @property
    def app_ref(self):
        return self.get_application()

    # ── Sidebar ──────────────────────────────────────────────
    def _build_sidebar(self):
        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        line1 = Gtk.Label(xalign=0, use_markup=True)
        line1.set_markup(f"<span foreground='{ACCENT}' weight='800'>▟</span> predatorctl")
        line1.add_css_class("brand")
        sub = Gtk.Label(label="CONTROL · PHN16-72", xalign=0)
        sub.add_css_class("brand-sub")
        brand.append(line1)
        brand.append(sub)

        header = Adw.HeaderBar()
        header.set_title_widget(brand)
        header.set_show_title(True)

        self.nav_list = Gtk.ListBox()
        self.nav_list.add_css_class("nav")
        self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_list.connect("row-selected", self._on_nav)
        self._nav_ids = []
        for pid, title, icon in self.NAV:
            self.nav_list.append(self._make_nav_row(title, icon))
            self._nav_ids.append(pid)

        # live footer
        self.foot_label = Gtk.Label(xalign=0, use_markup=True)
        foot = Gtk.Box()
        foot.add_css_class("side-foot")
        foot.append(self.foot_label)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nav_scroll.set_child(self.nav_list)
        nav_scroll.set_vexpand(True)
        nav_scroll.set_margin_top(6)
        body.append(nav_scroll)
        body.append(foot)

        tv = Adw.ToolbarView()
        tv.add_css_class("nav-sidebar")
        tv.add_top_bar(header)
        tv.set_content(body)
        return Adw.NavigationPage(title="predatorctl", child=tv)

    def _make_nav_row(self, title, icon):
        box = Gtk.Box(spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        img = Gtk.Image.new_from_icon_name(icon)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.add_css_class("nav-row-title")
        box.append(img)
        box.append(lbl)
        row = Gtk.ListBoxRow()
        row.add_css_class("nav-row")
        row.set_child(box)
        return row

    # ── Content ──────────────────────────────────────────────
    def _build_content(self):
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(160)
        for pid, _, _ in self.NAV:
            self.stack.add_named(self._pages[pid], pid)

        self.page_title = Gtk.Label(label="Dashboard")
        self.page_title.add_css_class("page-title")
        header = Adw.HeaderBar()
        header.set_title_widget(self.page_title)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.stack)
        scroller.set_vexpand(True)

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(scroller)

        tv = Adw.ToolbarView()
        tv.add_css_class("content-bg")
        tv.add_top_bar(header)
        tv.set_content(self.toast_overlay)
        return Adw.NavigationPage(title=APP_NAME, child=tv)

    def _on_nav(self, _list, row):
        if row is None:
            return
        idx = row.get_index()
        pid = self._nav_ids[idx]
        self.stack.set_visible_child_name(pid)
        self.page_title.set_label(self.NAV[idx][1])

    # ── API for the pages ────────────────────────────────────
    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)

    def request_refresh(self):
        self._tick()

    # ── Refresh loop ─────────────────────────────────────────
    def _tick(self):
        if self._refresh_lock:
            return GLib.SOURCE_CONTINUE
        self._refresh_lock = True

        def work():
            # Never let an exception kill the cycle: _apply_data ALWAYS runs
            # (otherwise _refresh_lock would stay stuck and refresh would die).
            try:
                data = self.app_ref.sensors.read_all()
            except Exception:
                data = None
            GLib.idle_add(self._apply_data, data)

        threading.Thread(target=work, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _apply_data(self, data):
        self._refresh_lock = False
        if data is None:
            return
        self.dashboard_page.refresh(data)
        self.temperatures_page.refresh(data)
        self.fan_page.refresh(data)
        self.profile_page.refresh(data)
        self.rgb_page.refresh(data)
        self.battery_page.refresh(data)
        self._update_footer(data)

    def _update_footer(self, data):
        cpu = data.cpu_temp
        prof = PROFILE_MAP.get(data.platform_profile)
        prof_name = prof[0] if prof else (data.platform_profile or "—")
        cpu_str = f"{cpu:.0f}°" if cpu else "--"
        self.foot_label.set_markup(
            f"<span font_family='monospace' foreground='{TEXT}'>CPU {cpu_str}</span>"
            f"   ·   {prof_name}"
        )
