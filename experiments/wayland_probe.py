"""Enumerate Wayland globals via libwayland-client (ctypes, no dependencies).

Used to verify, on the real compositor, whether protocols such as
``zwlr_layer_shell_v1`` are advertised. Does not need wayland-info or any
pip/conda package.

Run:
    python experiments/wayland_probe.py [protocol-name ...]
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys

GLOBAL_FUNC = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_char_p,
    ctypes.c_uint32,
)
REMOVE_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32)


class RegistryListener(ctypes.Structure):
    _fields_ = [("global_", GLOBAL_FUNC), ("global_remove", REMOVE_FUNC)]


def enumerate_globals() -> list[tuple[int, str, int]]:
    lib_name = ctypes.util.find_library("wayland-client") or "libwayland-client.so.0"
    wl = ctypes.CDLL(lib_name)

    wl.wl_display_connect.restype = ctypes.c_void_p
    wl.wl_display_connect.argtypes = [ctypes.c_char_p]
    wl.wl_display_roundtrip.restype = ctypes.c_int
    wl.wl_display_roundtrip.argtypes = [ctypes.c_void_p]
    wl.wl_display_disconnect.argtypes = [ctypes.c_void_p]
    # wl_display_get_registry() is a static-inline helper; use the underlying
    # marshal call with the wl_registry interface symbol instead.
    wl.wl_proxy_marshal_flags.restype = ctypes.c_void_p
    wl.wl_proxy_marshal_flags.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    wl.wl_proxy_add_listener.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(RegistryListener),
        ctypes.c_void_p,
    ]

    found: list[tuple[int, str, int]] = []

    @GLOBAL_FUNC
    def on_global(data, registry, name, interface, version):
        found.append((name, interface.decode("utf-8"), version))

    @REMOVE_FUNC
    def on_remove(data, registry, name):
        return None

    listener = RegistryListener(on_global, on_remove)

    display = wl.wl_display_connect(None)
    if not display:
        raise RuntimeError("cannot connect to Wayland display (WAYLAND_DISPLAY unset?)")
    try:
        registry_iface = ctypes.cast(
            ctypes.addressof(ctypes.c_char.in_dll(wl, "wl_registry_interface")),
            ctypes.c_void_p,
        )
        # opcode 1 == wl_display.get_registry, version 1, flags 0, arg NULL
        registry = wl.wl_proxy_marshal_flags(display, 1, registry_iface, 1, 0, None)
        wl.wl_proxy_add_listener(registry, ctypes.byref(listener), None)
        wl.wl_display_roundtrip(display)
        wl.wl_display_roundtrip(display)
    finally:
        wl.wl_display_disconnect(display)
    return found


def main() -> int:
    if not os.environ.get("WAYLAND_DISPLAY"):
        print("WAYLAND_DISPLAY not set; cannot probe native Wayland.")
        return 2
    protocols = sys.argv[1:] or ["zwlr_layer_shell_v1", "gtk_shell1", "wl_compositor"]
    globals_ = enumerate_globals()
    names = {g[1] for g in globals_}
    print(f"Wayland globals advertised: {len(globals_)}")
    for name in sorted(names):
        print(f"  - {name}")
    print("--- requested ---")
    for proto in protocols:
        print(f"{proto}: {'AVAILABLE' if proto in names else 'NOT AVAILABLE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
