"""
predatorctl UI package (driving adapter, GTK4/libadwaita).

Pins the GTK/Adw versions once, at package import, before any
`from gi.repository import ...` in the page modules.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
