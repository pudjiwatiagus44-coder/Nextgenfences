# Test compile a snippet
code = '''        dialog.setStyleSheet("""
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
        """)'''
exec(compile(code, '<test>', 'exec'))
print('Snippet compiles OK')