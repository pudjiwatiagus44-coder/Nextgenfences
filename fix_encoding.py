# Fix encoding for all Python files
import os

def fix_encoding(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Try to decode as UTF-8, if fails try GBK then decode to UTF-8
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = content.decode('gbk')
            # Re-encode as UTF-8
            content = text.encode('utf-8')
        except:
            return False
    
    # Write as UTF-8 with BOM
    with open(filepath, 'wb') as f:
        f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
        f.write(content)
    
    return True

# Find all Python files
root_dir = r'C:\Users\Administrator\Desktop\SKILL\MyDesktop'
for dirpath, _, filenames in os.walk(root_dir):
    # Skip __pycache__ and .venv
    if '__pycache__' in dirpath or '.venv' in dirpath:
        continue
    
    for filename in filenames:
        if filename.endswith('.py'):
            filepath = os.path.join(dirpath, filename)
            try:
                if fix_encoding(filepath):
                    print(f'Fixed: {filepath}')
                else:
                    print(f'Failed: {filepath}')
            except Exception as e:
                print(f'Error {filepath}: {e}')