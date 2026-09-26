import os
import re

directories = [
    r'c:\Kamal\BN'
]

extensions = {'.html', '.md', '.txt', '.py', '.css', '.js'}
exclude_files = {'bn_organic.db', 'store.db', 'rename.py'}

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    
    # 1. Hamro Organic Store -> Hamro Market
    new_content = re.sub(r'Hamro Organic Store', 'Hamro Market', new_content, flags=re.IGNORECASE)
    # 2. Hamro Organic -> Hamro Market
    new_content = re.sub(r'Hamro Organic', 'Hamro Market', new_content, flags=re.IGNORECASE)
    # 3. BN Organic Store -> Hamro Market
    new_content = re.sub(r'BN Organic Store', 'Hamro Market', new_content, flags=re.IGNORECASE)
    # 4. BN Organic -> Hamro Market
    new_content = re.sub(r'BN Organic', 'Hamro Market', new_content, flags=re.IGNORECASE)
    # 5. bn-organic -> hamro-market
    new_content = re.sub(r'bn-organic', 'hamro-market', new_content, flags=re.IGNORECASE)
    # 6. ORGANIC STORE -> Hamro Market (in _header.html: <h1>🌿 ORGANIC STORE</h1>)
    new_content = new_content.replace('ORGANIC STORE', 'Hamro Market')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for d in directories:
    for root, dirs, files in os.walk(d):
        if '.git' in root or '__pycache__' in root or 'node_modules' in root:
            continue
        for file in files:
            if file in exclude_files:
                continue
            ext = os.path.splitext(file)[1]
            if ext in extensions:
                filepath = os.path.join(root, file)
                try:
                    replace_in_file(filepath)
                except Exception as e:
                    print(f"Failed to process {filepath}: {e}")

print("Replacement complete.")
