with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\core\desktop_hook.py', 'rb') as f:
    content = f.read()

count = content.count(b'"""')
print(f'Triple quote count: {count}')

# Find all positions
import re
for m in re.finditer(b'"""', content):
    pos = m.start()
    line_num = content[:pos].count(b'\n') + 1
    line_start = content.rfind(b'\n', max(0, pos-60), pos)
    line_end = content.find(b'\n', pos)
    context = content[line_start+1:line_end+1][:60]
    print(f'Line {line_num}: {repr(context)}')