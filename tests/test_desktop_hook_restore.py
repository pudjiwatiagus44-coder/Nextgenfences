import unittest
from unittest.mock import Mock, patch


class FakeSignal:
    def __init__(self):
        self.connected = None

    def connect(self, callback):
        self.connected = callback


class FakeDesktopHook:
    def __init__(self):
        self.desktop_shown = FakeSignal()
        self.started_with = None

    def start(self, interval_ms):
        self.started_with = interval_ms


class DesktopHookRestoreTests(unittest.TestCase):
    def test_desktop_hook_restores_partitions_after_system_show_desktop(self):
        from main import NextGenDesktopApp

        app = object.__new__(NextGenDesktopApp)
        fake_hook = FakeDesktopHook()

        with patch("main.DesktopHook", return_value=fake_hook):
            with patch("main.QTimer.singleShot") as single_shot:
                app.start_desktop_hook()

                self.assertIs(app.desktop_hook, fake_hook)
                self.assertEqual(fake_hook.started_with, 300)
                self.assertIsNotNone(fake_hook.desktop_shown.connected)

                fake_hook.desktop_shown.connected()

                delays = [call.args[0] for call in single_shot.call_args_list]
                self.assertEqual(delays, [50, 250, 700])


if __name__ == "__main__":
    unittest.main()
