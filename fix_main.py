import re

with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
cleaned = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('#') or not stripped:
        cleaned.append(line)
        continue
    
    # Check if line is mostly garbled
    non_ascii_count = sum(1 for c in stripped if ord(c) > 127)
    if non_ascii_count > len(stripped) * 0.3 and len(stripped) > 50:
        continue
    
    cleaned.append(line)

content = '\n'.join(cleaned)

with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
