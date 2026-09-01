import re

def insert_csrf(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'X-CSRFToken' in content:
        return

    # Add csrf token extraction at top of file
    csrf_ext = "const csrfToken = document.querySelector('meta[name=\"csrf-token\"]')?.getAttribute('content');\n\n"
    content = csrf_ext + content

    # Find headers: { ... } and inject 'X-CSRFToken': csrfToken
    # Note: this is a simple replacement for fetch headers, assuming standard formatting.
    # We will replace headers: { with headers: { 'X-CSRFToken': csrfToken, 
    content = re.sub(r'headers:\s*\{', "headers: { 'X-CSRFToken': csrfToken,", content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Updated {filepath}')

insert_csrf(r'c:\Kamal\BN\static\js\main.js')
insert_csrf(r'c:\Kamal\BN\static\js\checkout.js')
insert_csrf(r'c:\Kamal\BN\static\js\admin.js')
