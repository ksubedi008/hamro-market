import os, re

for root, dirs, files in os.walk(r'c:\Kamal\BN\templates'):
    for file in files:
        if file.endswith('.html') and file != '_header.html' and file != 'dashboard.html' and 'admin' not in root:
            path = os.path.join(root, file)
            print('Processing ' + path)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = re.sub(r'<header>.*?</header>', '{% include \'_header.html\' %}', content, flags=re.DOTALL)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print('Updated ' + path)
