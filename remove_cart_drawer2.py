import os

def remove_cart_drawer(content):
    start_index = content.find('<div class="cart-drawer" id="cart-drawer">')
    if start_index == -1:
        return content

    # Find the closing div
    open_divs = 0
    i = start_index
    while i < len(content):
        if content[i:i+4] == '<div':
            open_divs += 1
            i += 4
        elif content[i:i+6] == '</div>':
            open_divs -= 1
            i += 6
            if open_divs == 0:
                return content[:start_index] + content[i:]
        else:
            i += 1
    
    return content

files_to_process = [
    r'c:\Kamal\BN\templates\index.html',
    r'c:\Kamal\BN\templates\orders.html',
    r'c:\Kamal\BN\templates\password.html',
    r'c:\Kamal\BN\templates\product-details.html'
]

for file in files_to_process:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = remove_cart_drawer(content)
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Removed cart drawer from {file}")
