"""
predatorctl - ui/rgb_page.py — keyboard RGB tab (4 zones).

On the PHN16-72 the backlight only lights up via four_zone_mode (animated
effects); static mode and per_zone_mode don't render. That's why the page is
built around effect + color + brightness + speed rather than static per-zone
colors.

This sysfs node has no meaningful read-back (writing R,G,B doesn't reliably
read back the same values), so the page can't ask the hardware what's
currently active. Instead, on first load it pre-fills itself from
Telemetry.kb_last_effect -- the same four_zone_mode string predatorctl-helper
already mirrors into /etc/predatorctl/restore.conf for boot restore. Without
this the page always opened on hardcoded defaults (Breathing/speed 4/red)
regardless of what was actually last set.
"""

from gi.repository import Gtk, Adw, Gdk

from constants import RGB_PRESETS, KB_EFFECTS, KB_EFFECTS_NO_SPEED, KB_EFFECTS_NO_COLOR


class RgbPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._suppress = False
        self._synced_once = False
        self._color = "ff0000"   # currently selected color (hex RRGGBB)
        self._build_ui()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)

        # Effect + brightness + speed
        fx_group = Adw.PreferencesGroup(title="Effect")

        self.effect_row = Adw.ComboRow(title="Mode")
        self.effect_row.set_model(Gtk.StringList.new([name for _, name in KB_EFFECTS]))
        self.effect_row.connect("notify::selected", self._on_param_changed)
        fx_group.add(self.effect_row)

        self.bright_row = Adw.SpinRow.new_with_range(0, 100, 5)
        self.bright_row.set_title("Brightness (%)")
        self.bright_row.set_value(100)
        self.bright_row.connect("notify::value", self._on_param_changed)
        fx_group.add(self.bright_row)

        self.speed_row = Adw.SpinRow.new_with_range(0, 9, 1)
        self.speed_row.set_title("Speed")
        self.speed_row.set_value(4)
        self.speed_row.connect("notify::value", self._on_param_changed)
        fx_group.add(self.speed_row)

        outer.append(fx_group)

        # Color presets — clicking applies immediately with the current effect
        presets_group = Adw.PreferencesGroup(title="Colors")
        self.color_flow = Gtk.FlowBox()
        self.color_flow.set_homogeneous(True)
        self.color_flow.set_column_spacing(8)
        self.color_flow.set_row_spacing(8)
        self.color_flow.set_min_children_per_line(5)
        self.color_flow.set_selection_mode(Gtk.SelectionMode.NONE)

        for name, hex_val in RGB_PRESETS:
            self.color_flow.append(self._make_color_swatch(name, hex_val))

        presets_group.add(self.color_flow)
        outer.append(presets_group)

        # Custom color + buttons
        custom_group = Adw.PreferencesGroup(title="Custom Color (Hex)")
        self.hex_entry = Adw.EntryRow(title="RRGGBB (e.g. ff00ff)")
        custom_group.add(self.hex_entry)

        btn_box = Gtk.Box(spacing=12)
        btn_box.set_margin_top(12)
        self.apply_btn = Gtk.Button(label="Apply Color")
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.set_hexpand(True)
        self.apply_btn.connect("clicked", self._on_custom_apply)
        btn_box.append(self.apply_btn)

        off_btn = Gtk.Button(label="Turn Off")
        off_btn.add_css_class("destructive-action")
        off_btn.set_hexpand(True)
        off_btn.connect("clicked", self._on_off_clicked)
        btn_box.append(off_btn)
        custom_group.add(btn_box)

        outer.append(custom_group)

        outer.append(Gtk.Label(vexpand=True))
        self.set_child(outer)
        self._update_widget_sensitivity(self._current_effect_mode())

    def _make_color_swatch(self, name, hex_val):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        r = int(hex_val[0:2], 16) / 255
        g = int(hex_val[2:4], 16) / 255
        b = int(hex_val[4:6], 16) / 255
        color = Gdk.RGBA()
        color.red, color.green, color.blue, color.alpha = r, g, b, 1.0

        swatch = Gtk.DrawingArea()
        swatch.set_content_height(40)
        swatch.set_draw_func(self._draw_color, color)
        box.append(swatch)

        lbl = Gtk.Label(label=name)
        lbl.add_css_class("caption")
        box.append(lbl)

        btn = Gtk.Button(child=box)
        btn.connect("clicked", lambda *_, h=hex_val: self._on_preset_clicked(h))
        return btn

    def _draw_color(self, area, cr, width, height, color):
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.arc(width / 2, height / 2, min(width, height) / 2 - 4, 0, 2 * 3.14159)
        cr.fill()

    def _current_effect_mode(self):
        return KB_EFFECTS[self.effect_row.get_selected()][0]

    def _update_widget_sensitivity(self, mode):
        """Some effects force speed or color to fixed values regardless of
        what we send (see KB_EFFECTS_NO_SPEED/KB_EFFECTS_NO_COLOR) -- grey
        out the controls that wouldn't do anything so the UI doesn't imply
        they're adjustable."""
        self.speed_row.set_sensitive(mode not in KB_EFFECTS_NO_SPEED)
        color_enabled = mode not in KB_EFFECTS_NO_COLOR
        self.color_flow.set_sensitive(color_enabled)
        self.hex_entry.set_sensitive(color_enabled)
        self.apply_btn.set_sensitive(color_enabled)

    def _apply(self):
        """Applies the current color + effect + brightness + speed."""
        ok, msg = self.app.control.set_kb_effect(
            mode=self._current_effect_mode(),
            color_hex=self._color,
            brightness=int(self.bright_row.get_value()),
            speed=int(self.speed_row.get_value()),
        )
        effect_name = KB_EFFECTS[self.effect_row.get_selected()][1]
        self.app.show_toast(f"RGB: {effect_name} #{self._color}" if ok else msg)

    def _on_preset_clicked(self, hex_val):
        self._color = hex_val
        self._apply()

    def _on_custom_apply(self, _):
        hex_val = self.hex_entry.get_text().strip().lstrip("#")
        if len(hex_val) != 6:
            self.app.show_toast("Invalid format. Use RRGGBB")
            return
        try:
            int(hex_val, 16)
        except ValueError:
            self.app.show_toast("Invalid hex")
            return
        self._color = hex_val
        self._apply()

    def _on_param_changed(self, *_):
        # Sensitivity must update even while suppressed (programmatic sync on
        # load) -- only the pkexec write below is gated by _suppress.
        self._update_widget_sensitivity(self._current_effect_mode())
        if self._suppress:
            return
        self._apply()

    def _on_off_clicked(self, _):
        ok, msg = self.app.control.set_kb_off()
        self.app.show_toast("Keyboard off" if ok else msg)

    def refresh(self, data):
        if self._synced_once or not data.kb_last_effect:
            return
        self._synced_once = True
        self._sync_from_last_effect(data.kb_last_effect)

    def _sync_from_last_effect(self, value):
        """Pre-fills effect/brightness/speed/color from the last value saved
        for boot restore -- see module docstring for why this is the only
        source of truth available."""
        parts = value.split(",")
        if len(parts) != 7:
            return
        try:
            mode, speed, brightness, _direction, r, g, b = (int(p) for p in parts)
        except ValueError:
            return
        idx = next((i for i, (eid, _) in enumerate(KB_EFFECTS) if eid == mode), None)
        if idx is None:
            return  # e.g. mode 0 (off) has no matching row to select
        self._suppress = True
        try:
            self.effect_row.set_selected(idx)
            self.bright_row.set_value(brightness)
            self.speed_row.set_value(speed)
        finally:
            self._suppress = False
        self._color = f"{r:02x}{g:02x}{b:02x}"
        self.hex_entry.set_text(self._color)
