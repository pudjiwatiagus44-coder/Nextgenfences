from pathlib import Path
text = Path("main.py").read_text(encoding="utf-8")
print(repr(text.splitlines()[10]))
print(repr(text.splitlines()[16]))
