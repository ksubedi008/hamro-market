import os
import re

cart_regex = re.compile(r'<div class="cart-drawer" id="cart-drawer">.*?</div>\s*</div>\s*</div>', re.DOTALL)

for root, dirs, files in os.walk(r'c:\Kamal\BN\templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            new_content = cart_regex.sub('', content)
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Removed cart drawer from {path}")
