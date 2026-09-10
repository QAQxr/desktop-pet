import logging
import os
import signal
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import main  # noqa: E402

SIGNAL_NAMES = ("SIGHUP", "SIGINT", "SIGTERM")


class FakeApp:
    def __init__(self):
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1


class LifecycleTest(unittest.TestCase):
    def test_signal_handlers_installed_and_quit(self):
        app = FakeApp()
        saved = {}
        for name in SIGNAL_NAMES:
            sig = getattr(signal, name, None)
            if sig is not None:
                saved[sig] = signal.getsignal(sig)
        try:
            main.install_signal_handlers(app, logging.getLogger("test-lifecycle"))
            for name in SIGNAL_NAMES:
                sig = getattr(signal, name, None)
                if sig is None:
                    continue
                self.assertTrue(callable(signal.getsignal(sig)), f"{name} handler missing")
            handler = signal.getsignal(signal.SIGHUP)
            handler(signal.SIGHUP, None)
            self.assertEqual(app.quit_calls, 1)
        finally:
            for sig, original in saved.items():
                signal.signal(sig, original)

    def test_quit_handler_is_idempotent_across_signals(self):
        app = FakeApp()
        saved = {}
        for name in SIGNAL_NAMES:
            sig = getattr(signal, name, None)
            if sig is not None:
                saved[sig] = signal.getsignal(sig)
        try:
            main.install_signal_handlers(app, logging.getLogger("test-lifecycle"))
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            self.assertEqual(app.quit_calls, 1)
        finally:
            for sig, original in saved.items():
                signal.signal(sig, original)


if __name__ == "__main__":
    unittest.main()
