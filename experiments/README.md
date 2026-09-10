# Display-layer / platform-backend feasibility (investigation)

This folder holds **throwaway feasibility probes**, not production code. They do
not import from or modify `src/`. They can be deleted at any time.

## Why

The user wants an eventual "pet display layer" that floats above the desktop,
lets the pet move inside it, and **lets clicks pass through transparent areas**
to the apps below. Layer Shell (`wlr-layer-shell`) is the natural fit on
wlroots/KDE, so we checked whether the current desktop supports it.

## Environment (verified on this machine)

| Item | Value |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| Desktop | GNOME (`XDG_CURRENT_DESKTOP=ubuntu:GNOME`), GNOME Shell 42.9 |
| Session | `XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY=wayland-0`, `DISPLAY=:0` (XWayland) |
| Compositor | Mutter (gnome-shell) |
| Qt | PySide6 6.11.2, platform plugin `wayland` (native) / `xcb` (XWayland) |

## Probes and results

### 1. `wayland_probe.py` — enumerate compositor globals

Dependency-free ctypes client (calls `libwayland-client` directly, no
`wayland-info` needed).

```bash
python experiments/wayland_probe.py zwlr_layer_shell_v1 gtk_shell1
```

Result on this machine:

```text
zwlr_layer_shell_v1: NOT AVAILABLE
gtk_shell1:          AVAILABLE
wl_compositor:       AVAILABLE
xdg_wm_base:         AVAILABLE
```

Advertised globals (26): `gtk_shell1`, `wl_compositor`, `wl_data_device_manager`,
`wl_drm`, `wl_output`, `wl_seat`, `wl_shm`, `wl_subcompositor`, `wp_presentation`,
`wp_viewporter`, `xdg_activation_v1`, `xdg_wm_base`, `zwp_linux_dmabuf_v1`,
`zwp_pointer_constraints_v1`, `zwp_relative_pointer_manager_v1`,
`zwp_text_input_manager_v3`, `zxdg_output_manager_v1`, ... — **no
`zwlr_layer_shell_v1`**.

Independently confirmed with a full protocol trace (`WAYLAND_DEBUG=1`): 0 matches
for `layer_shell`.

**Conclusion: GNOME/Mutter does not implement `wlr-layer-shell`.**

### 2. `mask_probe.py` — does `setMask` create an input region?

Plain masked translucent window (red ellipse), no DesktopWindow code.

- **Native Wayland** (`WAYLAND_DEBUG=1`): the client emits
  `wl_surface@N.set_input_region(wl_region@M)` → **input region is set**.
- **X11/XWayland**: `xwininfo -id <win> -shape` reports
  `Window shape extents: 200x200+150+100` (= mask × DPR 1.25) → **window/input
  shape applied**.

### 3. `x11_passthrough_probe.py` — real click-through (XTEST)

Two windows: an opaque background and a masked translucent "pet" on top.
Synthetic clicks via `XTestFakeButtonEvent` (libXtst, ctypes), DPR-corrected.

```bash
QT_QPA_PLATFORM=xcb python experiments/x11_passthrough_probe.py
```

Result:

```text
PASSTHROUGH_OUTSIDE=PASS   # click outside the mask reached the background app
PET_RECEIVES_INSIDE=PASS   # click inside the mask reached the pet
```

**Conclusion: region-based input passthrough works** (transparent area passes
clicks through, pet area receives them). This is the core input model the user
asked about.

## Options comparison

| Option | Works here? | Positioning | Input passthrough | Cost / risk |
|---|---|---|---|---|
| **A. Qt top-level window + `move()`** (current) | Yes | xcb: yes; native Wayland: **no** | Yes via `setMask` | Low; already implemented |
| **B. Layer Shell (`zwlr_layer_shell_v1`)** | **No on GNOME** | Free placement/anchors | Region-based | Needed for wlroots/KDE; new backend + per-compositor testing |
| **C. GNOME Shell Extension** | Possible, not built | Full control inside shell | Full control | High: JS/GJS, GNOME-version churn, install/enable UX, can't reuse PySide6 rendering directly |
| **D. Other DEs (KDE/wlroots)** | N/A (not installed) | Free (KWin supports layer-shell) | Region-based | Design should stay multi-backend |

> Note: B/C/D support claims for **other** compositors are from protocol/
> compositor documentation and were **not** tested in this environment (this
> machine only runs GNOME). Treat them as "expected, unverified".

## Recommendation

Keep the current **Qt top-level window backend** and, when a second backend is
needed, add it *behind the existing `PositioningService` abstraction* — do **not**
rewrite movement/animation.

```text
          Desktop Pet core (movement / animation / behavior)
                              │
                     DisplayBackend (abstract)
             ┌────────────────┼───────────────────────┐
   QtTopLevelBackend      LayerShellBackend        GnomeExtensionBackend
   (implemented now)      (future, wlroots/KDE)    (future, heavy; optional)
```

- **GNOME Wayland (current default):** use `xcb` for real movement; input
  passthrough via `setMask`. Native Wayland can display + set an input region
  but cannot be positioned freely.
- **wlroots / KDE Wayland:** a `LayerShellBackend` would be worthwhile later.
- **Do not** implement a Layer Shell backend now: it cannot run on the current
  GNOME environment, and the instructions forbid installing/switching
  compositors.

## Retention

Kept as reproducibility evidence + input-passthrough regression check. Delete
freely; nothing in `src/` depends on it.
