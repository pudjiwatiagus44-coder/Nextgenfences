import re

with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\main.py', 'rb') as f:
    content = f.read()

# Find all triple quote positions
pattern = b'"""'
positions = []
start = 0
while True:
    pos = content.find(pattern, start)
    if pos == -1:
        break
    positions.append(pos)
    start = pos + 1

print(f'Found {len(positions)} triple double quotes at positions:')
for i, pos in enumerate(positions):
    # Find line number
    line_num = content[:pos].count(b'\n') + 1
    # Show context
    line_start = content.rfind(b'\n', max(0, pos-50), pos)
    line_end = content.find(b'\n', pos)
    context = content[line_start+1:line_end+1]
    print(f'{i+1}. Position {pos}, Line {line_num}: {repr(context[:60])}')