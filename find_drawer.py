import os
for root, dirs, files in os.walk(r'c:\Kamal\BN\templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                if 'id="cart-drawer"' in f.read():
                    print(path)
