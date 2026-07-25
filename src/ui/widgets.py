"""
predatorctl - ui/widgets.py
Instrument widgets drawn with Cairo.

Gauge: 270° radial dial. Hairline track, value arc in the semantic
temperature color, monospace number centered. The dashboard's signature
element.
"""

import math

from gi.repository import Gtk

from constants import LINE, MUTED, ACCENT, temp_hex, _hex_rgb

_START = math.radians(135)          # arc start (bottom-left corner)
_SWEEP = math.radians(270)          # total sweep
_STROKE = 11


def panel(title, child, spacing=12):
    """The "instrument" card: uppercase title + content, used across the UI."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    box.add_css_class("panel")
    if title:
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.add_css_class("panel-title")
        box.append(lbl)
    box.append(child)
    return box


def metric(parent, label, value_text="--"):
    """Readout block (big mono value + small label). Returns the value Label."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    value = Gtk.Label(label=value_text, xalign=0)
    value.add_css_class("metric-value")
    cap = Gtk.Label(label=label, xalign=0)
    cap.add_css_class("metric-label")
    box.append(value)
    box.append(cap)
    parent.append(box)
    return value


class Sparkline(Gtk.DrawingArea):
    """
    Small history graph (line + fill). Fixed Y scale so different series
    (colors) stay comparable. Keeps its own sample buffer.
    """

    def __init__(self, height=44, vmin=30, vmax=100, maxlen=90):
        super().__init__()
        self._vals = []
        self._rgb = _hex_rgb(MUTED)
        self._vmin = vmin
        self._vmax = vmax
        self._maxlen = maxlen
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def push(self, value, color_hex):
        """Appends a sample (None is ignored) and redraws."""
        if value is not None:
            self._vals.append(value)
            if len(self._vals) > self._maxlen:
                self._vals = self._vals[-self._maxlen:]
            self._rgb = _hex_rgb(color_hex)
        self.queue_draw()

    def _draw(self, area, cr, width, height, *_):
        n = len(self._vals)
        if n < 2:
            return
        span = max(1e-6, self._vmax - self._vmin)
        pad = 3
        usable_h = height - 2 * pad
        step = width / (n - 1)

        def xy(i, v):
            frac = (min(self._vmax, max(self._vmin, v)) - self._vmin) / span
            return i * step, pad + (1 - frac) * usable_h

        r, g, b = self._rgb
        # fill under the line
        cr.move_to(0, height)
        for i, v in enumerate(self._vals):
            cr.line_to(*xy(i, v))
        cr.line_to((n - 1) * step, height)
        cr.close_path()
        cr.set_source_rgba(r, g, b, 0.14)
        cr.fill()
        # line
        cr.set_line_width(1.8)
        cr.set_line_join(1)   # round
        cr.set_source_rgb(r, g, b)
        cr.move_to(*xy(0, self._vals[0]))
        for i, v in enumerate(self._vals[1:], start=1):
            cr.line_to(*xy(i, v))
        cr.stroke()


class Gauge(Gtk.Overlay):
    """Radial dial for a temperature (0–100 °C)."""

    def __init__(self, label, size=132):
        super().__init__()
        self._frac = 0.0
        self._rgb = _hex_rgb(MUTED)

        self._area = Gtk.DrawingArea()
        self._area.set_content_width(size)
        self._area.set_content_height(size)
        self._area.set_draw_func(self._draw)
        self.set_child(self._area)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)

        self._value = Gtk.Label(label="--")
        self._value.add_css_class("gauge-value")

        self._name = Gtk.Label(label=label)
        self._name.add_css_class("gauge-label")

        center.append(self._value)
        center.append(self._name)
        self.add_overlay(center)

    def _set(self, text, frac, color_hex):
        self._value.set_label(text)
        self._frac = max(0.0, min(1.0, frac))
        self._rgb = _hex_rgb(color_hex)
        self._area.queue_draw()

    def set_temp(self, temp, vmax=100):
        """temp in °C or None (semantic temperature color)."""
        if temp is None:
            self._set("N/A", 0.0, MUTED)
        else:
            self._set(f"{temp:.0f}°", temp / vmax, temp_hex(temp))

    def set_percent(self, pct, color_hex=ACCENT, suffix="%"):
        """Generic percentage (battery, fan) with an explicit color."""
        if pct is None:
            self._set("N/A", 0.0, MUTED)
        else:
            self._set(f"{pct:.0f}{suffix}", pct / 100, color_hex)

    def set_text(self, text, color_hex=MUTED, frac=0.0):
        """Textual state without a numeric value (e.g. 'AUTO')."""
        self._set(text, frac, color_hex)

    def _draw(self, area, cr, width, height, *_):
        cx, cy = width / 2, height / 2
        r = min(width, height) / 2 - _STROKE / 2 - 2
        cr.set_line_cap(1)  # cairo.LINE_CAP_ROUND
        cr.set_line_width(_STROKE)

        # track
        tr, tg, tb = _hex_rgb(LINE)
        cr.set_source_rgb(tr, tg, tb)
        cr.arc(cx, cy, r, _START, _START + _SWEEP)
        cr.stroke()

        # value arc
        if self._frac > 0:
            r_, g_, b_ = self._rgb
            cr.set_source_rgb(r_, g_, b_)
            cr.arc(cx, cy, r, _START, _START + _SWEEP * self._frac)
            cr.stroke()
