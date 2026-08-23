with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\main.py', 'rb') as f:
    content = f.read()

# Count """ in lines around 252
lines = content.split(b'\n')
for i in range(248, 260):
    if i < len(lines):
        count = lines[i].count(b'"""')
        if count > 0:
            print(f'Line {i+1}: {repr(lines[i][:60])} - triple quote count: {count}')
        else:
            print(f'Line {i+1}: {repr(lines[i][:80])}')