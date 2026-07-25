"""
predatorctl - unit tests (stdlib unittest, no extra dependencies).

They run without GTK and without the hardware: they cover the pure domain
(constants, models, ports), the privileged helper's validation, and the
adapters' parsers/formats with subprocess/sysfs mocked.

Run from the project root:  python3 -m unittest discover tests -v
"""

import sys
from pathlib import Path

# The app modules import by absolute name (constants, domain, adapters…),
# same as main.py, which inserts src/ into sys.path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
