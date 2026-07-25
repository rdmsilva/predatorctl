#!/usr/bin/env python3
"""
predatorctl - Acer Predator control center (GTK4/libadwaita).

Entry point and composition root of the hexagonal architecture: instantiates
the concrete adapters (SensorAdapter, ControlAdapter) and injects them into
the application. The UI only knows the ports (domain/ports.py), so swapping
in a fake is a one-line change here.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from constants import APP_ID, CSS
from adapters.sysfs_sensors import SensorAdapter
from adapters.pkexec_control import ControlAdapter
from ui.window import PredatorWindow


class PredatorApp(Adw.Application):
    def __init__(self, sensors, control):
        super().__init__(application_id=APP_ID)
        # Injected ports — the UI reaches them via self.app.sensors / .control.
        self.sensors = sensors
        self.control = control
        self.window = None

    def do_activate(self):
        # Fixed dark theme — the "instrument" palette is designed for dark.
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        if not self.window:
            self.window = PredatorWindow(application=self)
        self.window.present()

    def show_toast(self, msg):
        if self.window:
            self.window.show_toast(msg)

    def request_refresh(self):
        if self.window:
            self.window.request_refresh()


def main():
    app = PredatorApp(sensors=SensorAdapter(), control=ControlAdapter())

    # CSS
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    app.run(sys.argv)


if __name__ == "__main__":
    main()
