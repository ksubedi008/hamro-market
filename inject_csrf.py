import os, re

for root, dirs, files in os.walk(r'c:\Kamal\BN\templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Avoid duplicate injection
            if 'csrf-token' in content:
                continue

            # Inject just before </head>
            new_content = re.sub(r'</head>', '    <meta name="csrf-token" content="{{ csrf_token() }}">\n</head>', content, flags=re.IGNORECASE)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print('Updated ' + path)
