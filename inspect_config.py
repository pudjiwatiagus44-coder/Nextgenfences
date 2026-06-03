import json
from pathlib import Path

path = Path("nextgen_config.json")
data = json.loads(path.read_text(encoding="utf-8"))
for fence in data.get("fences", []):
    print(fence["id"], len(fence.get("custom_order", [])))
