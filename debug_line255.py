with open(r'C:\Users\Administrator\Desktop\SKILL\MyDesktop\main.py', 'rb') as f:
    lines = f.readlines()

# Show raw bytes of line 255
line255 = lines[254]
print('Length:', len(line255))
print('Hex:', line255.hex())

# Check for weird characters
for i, b in enumerate(line255):
    if b > 127:
        try:
            ch = chr(b)
        except:
            ch = '?'
        print(f'Non-ASCII at {i}: {hex(b)} ({ch})')