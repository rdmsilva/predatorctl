"""
predatorctl - constants.py
IDs, design system (CSS + palette) and shared lookup tables.

Visual identity: "instrument cluster" — a dark, graphic telemetry panel with
radial gauges and monospace readouts. Color rule: TEAL is the interaction
color (chrome: active nav, switches, buttons); green/amber/red are reserved
for DATA (thermal state). Chrome never competes with data.
"""

APP_ID = "com.rafael.predatorctl"
APP_NAME = "Predator Control"

# ─── Palette (single source for CSS and the Cairo gauge drawing) ───────────
INK = "#0e1217"          # app background
SIDEBAR = "#0a0d12"      # sidebar, recessed
PANEL = "#161c24"        # elevated card
PANEL_2 = "#1e2632"      # hover / surface 2
LINE = "#273040"         # hairline / gauge track
TEXT = "#e9edf3"
MUTED = "#7b8697"
ACCENT = "#1ec8b6"       # teal — interaction
# Temperature semantics (data only)
COOL = "#3ddc97"
WARM = "#f5c451"
HOT = "#ff5d6c"

# Temperature thresholds (°C)
T_WARM = 60
T_HOT = 80


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def temp_class(temp):
    if temp is None:
        return ""
    if temp < T_WARM:
        return "temp-cool"
    if temp < T_HOT:
        return "temp-warm"
    return "temp-hot"


def temp_hex(temp):
    """Semantic color hex for a temperature (MUTED when unknown)."""
    if temp is None:
        return MUTED
    if temp < T_WARM:
        return COOL
    if temp < T_HOT:
        return WARM
    return HOT


def temp_rgb(temp):
    """(r,g,b) in 0..1 for Cairo drawing."""
    return _hex_rgb(temp_hex(temp))


# ─── CSS (design system) ───────────────────────────────────────────────────
CSS = f"""
/* libadwaita uses TEAL as the global accent (switches, spinrows, focus) */
@define-color accent_color {ACCENT};
@define-color accent_bg_color {ACCENT};
@define-color accent_fg_color #04120f;

/* The whole libadwaita stack adopts the "instrument" palette (boxed-lists,
   rows, headerbars, cards) without per-widget CSS. */
@define-color window_bg_color {INK};
@define-color window_fg_color {TEXT};
@define-color view_bg_color {INK};
@define-color view_fg_color {TEXT};
@define-color card_bg_color {PANEL};
@define-color card_fg_color {TEXT};
@define-color headerbar_bg_color {INK};
@define-color headerbar_fg_color {TEXT};
@define-color popover_bg_color {PANEL};
@define-color popover_fg_color {TEXT};

@define-color ink {INK};
@define-color panel {PANEL};
@define-color panel2 {PANEL_2};
@define-color line {LINE};
@define-color muted {MUTED};
@define-color teal {ACCENT};

window.instrument {{ background-color: {INK}; }}

/* ── Sidebar ───────────────────────────────────────── */
.nav-sidebar {{ background-color: {SIDEBAR}; }}
.nav-sidebar headerbar {{ background-color: {SIDEBAR}; box-shadow: none; }}

.brand {{
    font-weight: 800;
    font-size: 15px;
    color: {TEXT};
}}
.brand-mark {{
    color: {ACCENT};
    font-weight: 800;
}}
.brand-sub {{
    font-size: 10px;
    color: {MUTED};
}}

/* nav rows */
list.nav {{ background: transparent; }}
row.nav-row {{
    border-radius: 10px;
    margin: 2px 8px;
    padding: 2px 6px;
    color: {MUTED};
}}
row.nav-row:hover {{ background-color: {PANEL}; color: {TEXT}; }}
row.nav-row:selected {{
    background-color: alpha({ACCENT}, 0.14);
    color: {TEXT};
    box-shadow: inset 3px 0 0 0 {ACCENT};
}}
row.nav-row:selected image {{ color: {ACCENT}; }}
.nav-row-title {{ font-size: 14px; font-weight: 600; }}

/* live sidebar footer */
.side-foot {{
    border-top: 1px solid {LINE};
    padding: 10px 14px;
    color: {MUTED};
    font-size: 12px;
}}
.side-foot .mono {{ color: {TEXT}; }}

/* ── Content ───────────────────────────────────────── */
.content-bg {{ background-color: {INK}; }}
.content-bg headerbar {{ background-color: {INK}; box-shadow: none; }}
.page-title {{ font-weight: 700; }}

/* ── Panels / cards ────────────────────────────────── */
.panel {{
    background-color: {PANEL};
    border: 1px solid {LINE};
    border-radius: 16px;
    padding: 16px;
}}
.panel-title {{
    font-size: 11px;
    font-weight: 700;
    color: {MUTED};
}}

/* gauges in the cluster must not get FlowBox selection/focus highlight */
flowboxchild {{ background: none; padding: 6px; }}
flowboxchild:selected,
flowboxchild:focus,
flowboxchild:hover,
flowboxchild:active {{ background: none; box-shadow: none; outline: none; }}

/* numeric readouts in monospace (instrument) */
.readout {{
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", monospace;
    font-feature-settings: "tnum" 1;
}}
.gauge-value {{
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", monospace;
    font-size: 30px;
    font-weight: 700;
    color: {TEXT};
}}
.gauge-unit {{ font-size: 12px; color: {MUTED}; }}
.gauge-label {{
    font-size: 10px;
    font-weight: 700;
    color: {MUTED};
}}

.temp-cool {{ color: {COOL}; }}
.temp-warm {{ color: {WARM}; }}
.temp-hot  {{ color: {HOT}; }}

/* compact metric (GPU/RAM detail) */
.metric-value {{
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 18px;
    font-weight: 700;
    color: {TEXT};
}}
.metric-label {{ font-size: 10px; font-weight: 700; color: {MUTED}; }}

/* compact core cell (Temperatures page) */
.panel.mini {{ padding: 10px; border-radius: 12px; }}
.core-temp {{
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 13px;
    font-weight: 700;
    color: {TEXT};
}}

/* status chips */
.status-chip {{
    background-color: {PANEL};
    border: 1px solid {LINE};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    color: {TEXT};
}}
.status-chip .dot {{ color: {ACCENT}; }}

/* profile buttons */
.profile-btn {{
    background-color: {PANEL};
    border: 1px solid {LINE};
    border-radius: 16px;
    padding: 18px;
}}
.profile-btn:hover {{ background-color: {PANEL_2}; }}
.profile-btn.active {{
    background-color: alpha({ACCENT}, 0.16);
    border-color: {ACCENT};
}}
"""

PROFILE_MAP = {
    "low-power": ("Quiet", "Minimal fan, power saving"),
    "quiet": ("Quiet", "Minimal fan, power saving"),
    "balanced": ("Balanced", "Good for daily use"),
    "balanced-performance": ("Performance", "More aggressive"),
    "performance": ("Turbo", "Maximum performance"),
}

RGB_PRESETS = [
    ("Red", "ff0000"),
    ("Green", "00ff00"),
    ("Blue", "0000ff"),
    ("White", "ffffff"),
    ("Purple", "8000ff"),
    ("Cyan", "00ffff"),
    ("Pink", "ff00ff"),
    ("Orange", "ff8800"),
    ("Yellow", "ffff00"),
]

# Keyboard RGB effects (the `mode` field of four_zone_mode). On the PHN16-72
# static mode (0) does not light up — only the animated effects below.
# (id, friendly_name)
KB_EFFECTS = [
    (1, "Breathing"),
    (2, "Neon"),
    (3, "Wave"),
    (4, "Shifting"),
    (5, "Zoom"),
]
