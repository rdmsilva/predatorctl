# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`predatorctl` is a GTK4/libadwaita GUI (Python 3 + PyGObject) for controlling an **Acer Predator PHN16-72** laptop on Linux. It reads sensors and drives hardware through the already-installed `linuwu_sense` kernel module via sysfs — there is no kernel module of its own. Code, comments and UI strings are all in English; `README.pt-BR.md` is the only Portuguese file in the repo.

### Why this design (security intent — do not erode)

The project was written from scratch specifically to avoid the privilege surface common in pre-existing tools for this hardware: passwordless polkit rules, custom closed kernel modules, direct `/dev/ec` Embedded Controller access, and `curl | sudo bash` installers. predatorctl's **entire** privilege surface is the one small pkexec helper below, which prompts for a password every time and only writes whitelisted, validated actions. Keeping that surface minimal is the whole point — when adding features, do not introduce a passwordless polkit rule, a kernel module, EC access, or any privileged path outside the helper.

For the kernel-module layer, this machine deliberately blacklists the native `acer_wmi` (`/etc/modprobe.d/`) and loads [`linuwu_sense`](https://github.com/0x7375646F/Linuwu-Sense) instead (`/etc/modules-load.d/`, unloaded on shutdown by `linuwu_sense.service`). `linuwu_sense` claims the same WMI GUIDs as `acer_wmi` but additionally exposes the `predator_sense/*` sysfs knobs the native driver doesn't — so the paths this app reads/writes exist *only* because of that swap. It's still a full-access kernel module, but an open-source auditable one. This is an environment prerequisite, not part of the app: the repo only offers `install-linuwu-dkms.sh`, an **optional**, explicit `sudo` helper that installs upstream Linuwu-Sense via DKMS (so kernel updates rebuild it) — the app itself never touches kernel code, and `install.sh` doesn't call it.

## Running

```bash
python3 src/main.py          # dev: run from the source tree
```

Or install system-wide (adds a launcher, `.desktop` menu entry, icon, and the polkit rule):

```bash
sudo ./install.sh            # → /usr/local/lib/predatorctl, `predatorctl` command
sudo ./uninstall.sh          # remove everything it created
```

**Two run modes, one difference — auth.** The `pkexec` helper is invoked **directly** (`pkexec <helper> …`, not `pkexec python3 <helper>`) so the polkit rule can match it by program path. Installed, the helper lives at a **root-owned** `/usr/local/lib/predatorctl/helper/predatorctl-helper` and the rule (`data/49-predatorctl.rules` → `/etc/polkit-1/rules.d/`) grants **`auth_admin_keep`** — password once per ~5-min session, **not** passwordless. Run from source, the helper path doesn't match the rule, so every action prompts (fine for dev). Making the helper root-owned is what makes cached auth safe (a user-writable root-run script would be an escalation vector). `PROFILE_MAP`-style install assets live in `data/` (`.desktop`, icon SVG, polkit rule).

Requires system packages (not a venv/pip project — PyGObject binds to system GTK): `python-gobject`, `gtk4`, `libadwaita`, `lm_sensors`, `nvidia-utils`, and the loaded `linuwu_sense` kernel module. There is no test suite, linter config, or build step. `src/main.py` inserts its own directory on `sys.path`, so the `domain`, `adapters`, `ui`, and `constants` modules import by absolute name regardless of CWD.

Realistic behavior depends on the target hardware: reads degrade to `None`/`"N/A"` off-device, and writes will fail the pkexec call. **Sensors are auto-detected by chip *type*** via `sensors -j` (Intel `coretemp` or AMD `k10temp`/`zenpower`; any `nvme-*`; any `spd5118-*`/`jc42-*`; NVIDIA via `nvidia-smi` with an `amdgpu` temperature fallback) — not hardcoded addresses — so temperatures work across the Predator/Nitro family, not just the PHN16-72. The **controls** still require `linuwu_sense` exposing its `predator_sense/`+`four_zoned_kb/` sysfs (the supported Predator/Nitro gaming models); on anything else the reads return `N/A` and writes fail cleanly (no damage).

## Architecture

**Hexagonal (ports & adapters).** The layout exists to make the project's one security-critical boundary — unprivileged reads vs. privileged writes — explicit and swappable. Dependencies point inward: `ui` and `adapters` depend on `domain`; `domain` depends on nothing.

- **`src/domain/`** — the center, no GTK/sysfs/subprocess imports. `models.py` holds the `Telemetry`/`GpuInfo`/`Battery` dataclasses (a full hardware snapshot). `ports.py` defines two `@runtime_checkable` Protocols: `SensorPort` (read) and `ControlPort` (write). Every control method returns `(success: bool, message: str)`.
- **`src/adapters/sysfs_sensors.py`** — `SensorAdapter` implements `SensorPort`. `read_all()` is the single aggregator the UI calls every 2s; it returns a `Telemetry` built from sysfs reads (`linuwu_sense`, `platform_profile`, `BAT1`) plus subprocess scrapes of `sensors` and `nvidia-smi`. Every reader swallows errors and returns `None`/empty so the UI never crashes on missing hardware.
- **`src/adapters/pkexec_control.py`** — `ControlAdapter` implements `ControlPort`. Every setter funnels through `_pkexec_write(action, value)`, which shells out to `pkexec <python> helper/predatorctl-helper <action> <value>`. Args go on the **command line, not stdin** (pkexec does not forward stdin). `HELPER` is resolved via `Path(__file__).resolve().parents[2]`, so this file must stay two levels below the project root.
- **`helper/predatorctl-helper`** — the only code that runs as root, and the actual security boundary. A minimal script that refuses to run unless `geteuid()==0`, enforces an `ACTIONS` whitelist mapping action names to exact sysfs paths, and `validate()`s each value before writing. **Any new privileged capability must be added to both `ACTIONS` and `validate()` here, kept strict, and never bypass this helper** (see the "Why this design" section).
- **`src/ui/`** — the driving adapter (GTK4/libadwaita). One page per file (`dashboard`, `temperatures_page`, `fan_page`, `profile_page`, `rgb_page`, `battery_page`); `window.py` hosts them in a `Gtk.Stack` inside an `Adw.NavigationSplitView` (lateral sidebar with a `Gtk.ListBox` nav + a live footer readout). `ui/widgets.py` holds the shared instrument pieces: the Cairo `Gauge` (radial arc) plus `panel()`/`metric()` builders. `ui/__init__.py` pins the GTK/Adw versions once. The UI depends only on the **ports**, never the concrete adapters. `PREDATOR_PAGE=<0-5>` opens the app directly on a given tab (handy for screenshots).
- **`src/main.py`** — the composition root. Instantiates `SensorAdapter()` and `ControlAdapter()`, injects them into `PredatorApp(sensors=..., control=...)`, and forces the dark color scheme (`Adw.StyleManager`). Swapping in a fake (off-device, tests) is a one-line change here and nothing else. Pages reach the ports through the app: `self.app.sensors` / `self.app.control` (the window exposes the app via its `app_ref` property).
- **`src/constants.py`** — leaf module (no imports): `APP_ID`, the **design system** (palette constants like `INK`/`PANEL`/`ACCENT`/`COOL`/`WARM`/`HOT` feeding both the CSS f-string and the Cairo drawing), `PROFILE_MAP`, `RGB_PRESETS`, `KB_EFFECTS`, and `temp_class`/`temp_hex`/`temp_rgb`. The design language is documented in the `ui-design-language` memory. Importable from anywhere without creating cycles.
- **`helper/predatorctl-restore`** — optional, opt-in boot-time preference restore (see below). Contains no privileged logic of its own: it reads `/etc/predatorctl/restore.conf` and shells out to `predatorctl-helper` for each line, so it can't be used to bypass the whitelist/`validate()` boundary above.

### Refresh loop and threading

`PredatorWindow._tick()` runs on a `GLib.timeout_add_seconds(2, ...)`. It offloads the blocking `self.app_ref.sensors.read_all()` (subprocess calls) to a daemon thread, then marshals the resulting `Telemetry` back to the main loop with `GLib.idle_add(self._apply_data, ...)`. `_refresh_lock` prevents overlapping ticks. **Never call GTK from the worker thread — always hop back via `idle_add`.** Each page implements `refresh(telemetry)`; `RgbPage.refresh` is intentionally a no-op (RGB has no meaningful read-back).

Pages that both display and control state (Fan, Battery) use a `_suppress_signal`/`_suppress` flag: set it before programmatically updating a widget so the `notify::active`/`notify::value` handler doesn't fire a spurious pkexec write during a refresh.

### Boot-time preference restore (optional, opt-in)

predatorctl has no daemon, and `linuwu_sense` comes back with its own driver defaults every boot — so without this, the last profile/RGB/battery-limiter values set in the GUI are lost on reboot. `predatorctl-restore.service` (`data/predatorctl-restore.service`, `Type=oneshot`, `WantedBy=multi-user.target`, gated by `ConditionPathExists=/etc/predatorctl/restore.conf`) re-applies them at boot.

This is a second, distinct root-run path from the GUI's, so it's worth being explicit about why it doesn't erode the "one privileged surface" rule in "Why this design": the systemd unit runs `helper/predatorctl-restore` **as root directly, without `pkexec`** — there is no interactive session at boot to prompt for a password, and pkexec exists precisely to bridge that gap for an unprivileged user session, which doesn't apply here. `predatorctl-restore` itself never touches sysfs; it parses `/etc/predatorctl/restore.conf` (`action=value` lines) and, for each one, calls `predatorctl-helper <action> <value>` exactly like `pkexec_control.py` does — same whitelist, same `validate()`, same single point of enforcement. The only new trust requirement is that `/etc/predatorctl/restore.conf` stays root-owned/non-user-writable (installed dir is `root:root 755`, matching `APP_DIR`'s rationale) — anyone who could write to it could get the always-root restore step to write arbitrary *whitelisted, validated* values, which is a much smaller hole than a new privileged path would be, but still worth keeping in mind if this is extended.

`install.sh` installs the unit, the `/etc/predatorctl/` dir and `restore.conf.example`, but does **not** enable or create `restore.conf` — it stays fully inert until the user explicitly opts in (`sudo systemctl enable --now predatorctl-restore.service`), same posture as `install-linuwu-dkms.sh`.

### Value formats (must stay in sync across the layers)

- **fan_speed**: `"0,0"` = auto (EC control); `"CPU%,GPU%"` = manual, each 0–100. `SensorAdapter.read_fan_speed()` returns `None` for auto, else a `(cpu, gpu)` tuple on `Telemetry.fan_speed`.
- **platform_profile**: one of `low-power`, `quiet`, `balanced`, `balanced-performance`, `performance`. Mapped to friendly names via `PROFILE_MAP` in `constants.py`; the Profile page writes these directly via `set_platform_profile`.
  - **AC-power gate (PHN16-72) — not a driver gap:** `linuwu_sense` maps these to real Acer thermal profiles (`low-power`=Eco, `balanced`=Balanced, `balanced-performance`=Performance, `performance`=**Turbo**). It deliberately blocks `performance`, `balanced-performance`, and `quiet` with `EOPNOTSUPP` (Errno 95) when **on battery** — matching official PredatorSense (no turbo unplugged). On **AC** all work. (Verified against the driver source: `acer_predator_v4_platform_profile_set` checks `on_AC` before those profiles.) So `Telemetry.on_ac` (from `read_on_ac`) drives the UI: `ProfilePage` disables Performance/Turbo on battery and, if a write still returns EOPNOTSUPP, shows a "requires AC" toast rather than a false success.
- **keyboard RGB** (`four_zoned_kb/four_zone_mode`): `"mode,speed,brightness,direction,R,G,B"` — effect `mode` 0–7, `speed` 0–9, `brightness` 0–100, `direction` 0–2, and `R`/`G`/`B` as **decimal** 0–255. `ControlAdapter.set_kb_effect()` builds this from an effect id + hex color; `set_kb_off()` writes `"0,0,0,0,0,0,0"`. Effect ids live in `KB_EFFECTS` (`constants.py`).
  - **Hardware quirk (PHN16-72):** the keyboard backlight only renders via `four_zone_mode` **animated effects** (mode ≥ 1). The static `per_zone_mode` node (old `rgb` action, `"hex,hex,hex,hex,brightness"`) and `four_zone_mode` static mode `0` accept writes but leave the LEDs dark. The `rgb` action still exists in the helper for generality, but the UI drives `four_zone_mode`. Don't "fix" the RGB page back to solid/per-zone colors — it won't light this machine.
- **toggles** (battery_limiter, lcd_override, backlight_timeout): `"0"`/`"1"`.

The `validate()` whitelist in the helper, the `_pkexec_write` calls in `pkexec_control.py`, and the parsers in `sysfs_sensors.py` all encode these formats independently — a format change must touch all three.
