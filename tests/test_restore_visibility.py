import unittest
from unittest.mock import patch


class FakeFence:
    def __init__(self):
        self.recovered = False

    def recover_after_show_desktop(self):
        self.recovered = True

    def winId(self):
        return 12345


class RestoreVisibilityTests(unittest.TestCase):
    def test_restore_does_not_reembed_partition_windows(self):
        from main import NextGenDesktopApp

        app = object.__new__(NextGenDesktopApp)
        fence = FakeFence()
        app.fences = {"partition": fence}

        with patch("main.win32gui.ShowWindow"), patch("main.win32gui.SetWindowPos"):
            with patch("main.QTimer.singleShot", side_effect=lambda _ms, fn: fn()):
                app.restore_all_fences()

        self.assertFalse(fence.recovered)


if __name__ == "__main__":
    unittest.main()
