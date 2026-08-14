import unittest
from unittest.mock import Mock, patch


class FakeApp:
    def topLevelWidgets(self):
        return []


class ShowDesktopTests(unittest.TestCase):
    def test_show_desktop_does_not_minimize_partition_windows(self):
        from widgets.floating_ball import FloatingBallWidget

        ball = FloatingBallWidget.__new__(FloatingBallWidget)

        def enumerate_one_partition(callback, _param):
            callback(111, None)

        with patch("widgets.floating_ball.QApplication.instance", return_value=FakeApp()):
            with patch("widgets.floating_ball.win32gui.EnumWindows", side_effect=enumerate_one_partition):
                with patch("widgets.floating_ball.win32gui.IsWindowVisible", return_value=True):
                    with patch("widgets.floating_ball.win32gui.GetClassName", return_value="QtWindow"):
                        with patch("widgets.floating_ball.is_partition_window", return_value=True, create=True):
                            with patch(
                                "widgets.floating_ball.win32gui.GetWindowPlacement",
                                return_value=(0, 1, (0, 0), (0, 0), (0, 0, 0, 0)),
                            ):
                                with patch("widgets.floating_ball.win32gui.ShowWindow") as show_window:
                                    ball.show_desktop()

        show_window.assert_not_called()


if __name__ == "__main__":
    unittest.main()
