"""
predatorctl - ui/profile_page.py — thermal profiles (real Acer thermal profiles).

Each card writes a platform_profile that linuwu_sense maps to a real Acer
thermal profile: low-power=Eco, balanced=Balanced, balanced-performance=
Performance, performance=Turbo. The firmware BLOCKS Performance/Turbo (and
quiet) when unplugged (EOPNOTSUPP) — same as official PredatorSense. That's
why the AC-only cards are disabled on battery. See CLAUDE.md.
"""

from gi.repository import Gtk

# (platform_profile, name, description, icon, requires_ac)
PROFILES = [
    ("low-power", "Quiet", "Eco,\nminimal fan", "🎭", False),
    ("balanced", "Balanced", "Good for\ndaily use", "⚖️", False),
    ("balanced-performance", "Performance", "More aggressive\n(requires AC)", "⚡", True),
    ("performance", "Turbo", "Acer Turbo,\nmaximum (requires AC)", "🔥", True),
]


class ProfilePage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.app = app
        self.profile_buttons = {}     # prof_id -> (button, requires_ac)
        self._on_ac = True
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._build_ui()

    def _build_ui(self):
        self.hint = Gtk.Label(
            label="System thermal profile. Performance and Turbo (Acer Turbo) "
                  "only work with the charger plugged in, as in PredatorSense.",
            xalign=0, wrap=True)
        self.hint.add_css_class("panel-title")
        self.append(self.hint)

        flow = Gtk.FlowBox()
        flow.set_homogeneous(True)
        flow.set_column_spacing(12)
        flow.set_row_spacing(12)
        flow.set_min_children_per_line(2)
        flow.set_max_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)

        for prof_id, name, desc, icon, requires_ac in PROFILES:
            btn = self._make_profile_button(prof_id, name, desc, icon)
            self.profile_buttons[prof_id] = (btn, requires_ac)
            flow.append(btn)

        self.append(flow)
        self.append(Gtk.Box(vexpand=True))

    def _make_profile_button(self, prof_id, name, desc, icon):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.set_css_classes(["title-1"])
        name_lbl = Gtk.Label(label=name)
        name_lbl.add_css_class("title-2")
        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.add_css_class("caption")
        desc_lbl.set_wrap(True)
        desc_lbl.set_justify(Gtk.Justification.CENTER)

        box.append(icon_lbl)
        box.append(name_lbl)
        box.append(desc_lbl)

        btn = Gtk.Button(child=box)
        btn.add_css_class("profile-btn")
        btn.connect("clicked", lambda *_, pid=prof_id, n=name: self._on_profile_clicked(pid, n))
        return btn

    def _on_profile_clicked(self, prof_id, name):
        requires_ac = self.profile_buttons[prof_id][1]
        if requires_ac and not self._on_ac:
            self.app.show_toast(f"'{name}' requires the charger plugged in (AC)")
            return
        ok, msg = self.app.control.set_platform_profile(prof_id)
        if ok:
            self.app.show_toast(f"Profile: {name}")
        elif "not supported" in msg or "Errno 95" in msg:
            self.app.show_toast(f"'{name}' requires the charger plugged in (AC)")
        else:
            self.app.show_toast(f"Failed to apply '{name}': {msg}")
        self.app.request_refresh()

    def refresh(self, data):
        self._on_ac = data.on_ac
        current = data.platform_profile
        for prof_id, (btn, requires_ac) in self.profile_buttons.items():
            # active
            if prof_id == current:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
            # disable Performance/Turbo on battery
            btn.set_sensitive(self._on_ac or not requires_ac)
