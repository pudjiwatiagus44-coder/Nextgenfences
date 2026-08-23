from pathlib import Path
for enc in ["utf-8", "utf-8-sig", "utf-16", "utf-16le", "utf-16be", "utf-32", "gbk", "gb18030", "big5", "latin1"]:
    try:
        Path("main.py").read_text(encoding=enc)
        print("OK", enc)
    except Exception as exc:
        print("FAIL", enc, exc)
