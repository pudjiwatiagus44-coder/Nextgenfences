import unittest
from unittest.mock import patch


class DesktopHookTests(unittest.TestCase):
    def test_hidden_fence_triggers_shown_signal(self):
        """A hidden fence window should cause desktop_shown to emit."""
        from core.desktop_hook import DesktopHook

        hook = DesktopHook()
        hook.set_fence_hwnds([12345])
        emitted = []
        hook.desktop_shown.connect(lambda: emitted.append(True))

        with patch("core.desktop_hook.win32gui.IsWindow", return_value=True):
            with patch("core.desktop_hook.win32gui.IsWindowVisible", return_value=False):
                hook._check_fence_visibility()

        self.assertTrue(emitted)

    def test_visible_fence_does_not_trigger(self):
        """A visible fence window should NOT emit desktop_shown."""
        from core.desktop_hook import DesktopHook

        hook = DesktopHook()
        hook.set_fence_hwnds([12345])
        emitted = []
        hook.desktop_shown.connect(lambda: emitted.append(True))

        with patch("core.desktop_hook.win32gui.IsWindow", return_value=True):
            with patch("core.desktop_hook.win32gui.IsWindowVisible", return_value=True):
                with patch("core.desktop_hook.win32gui.IsIconic", return_value=False):
                    hook._check_fence_visibility()

        self.assertFalse(emitted)

    def test_minimized_fence_triggers_shown_signal(self):
        """A minimized (iconic) fence window should emit desktop_shown."""
        from core.desktop_hook import DesktopHook

        hook = DesktopHook()
        hook.set_fence_hwnds([12345])
        emitted = []
        hook.desktop_shown.connect(lambda: emitted.append(True))

        with patch("core.desktop_hook.win32gui.IsWindow", return_value=True):
            with patch("core.desktop_hook.win32gui.IsWindowVisible", return_value=True):
                with patch("core.desktop_hook.win32gui.IsIconic", return_value=True):
                    hook._check_fence_visibility()

        self.assertTrue(emitted)

    def test_invalid_hwnd_does_not_crash(self):
        """An invalid HWND should be skipped, not crash."""
        from core.desktop_hook import DesktopHook

        hook = DesktopHook()
        hook.set_fence_hwnds([99999])
        emitted = []
        hook.desktop_shown.connect(lambda: emitted.append(True))

        with patch("core.desktop_hook.win32gui.IsWindow", return_value=False):
            hook._check_fence_visibility()

        self.assertFalse(emitted)


if __name__ == "__main__":
    unittest.main()
