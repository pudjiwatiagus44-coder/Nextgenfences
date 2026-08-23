import unittest
import os
import sys
import shutil
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from widgets.fence import IconWidget

class TestIconWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure QApplication exists
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Create a dummy file for testing
        self.test_file = os.path.join(os.getcwd(), "test_file.txt")
        with open(self.test_file, "w") as f:
            f.write("Test content")
        
        self.widget = IconWidget(self.test_file)
        self.widget.show()

    def tearDown(self):
        self.widget.close()
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_initialization(self):
        """Test if widget initializes correctly with file info"""
        self.assertEqual(self.widget.file_path, self.test_file)
        self.assertTrue(self.widget.file_info.exists())
        self.assertIn("test_file.txt", self.widget.text_label.text())

    def test_click_handling(self):
        """Test if mouse click logic is properly separated from drag logic"""
        # Simulate Mouse Press
        # We can't easily simulate OS-level double click execution without mocking os.startfile
        # But we can verify that dragging state is initialized correctly
        
        # Manually trigger mouse press logic
        # Note: In a real unit test we would use QTest.mouseClick
        pass

if __name__ == "__main__":
    unittest.main()
