import os
import re

for root, dirs, files in os.walk(r'c:\Kamal\BN\templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all <form ...> tags
            # We want to insert the CSRF token just after the <form> tag, 
            # but ONLY if it's a POST form or doesn't have method="GET".
            # To be safe and follow instructions, we'll inject into <form ... method="POST" ...>
            
            # Function to replace
            def replacer(match):
                form_tag = match.group(0)
                # If it's explicitly method="GET", skip it
                if re.search(r'method=[\'"]GET[\'"]', form_tag, re.IGNORECASE):
                    return form_tag
                
                # Check if csrf_token is already right after it
                # Not doing complex lookahead, just we'll check if the whole file already has it, 
                # but a file could have multiple forms.
                return form_tag + '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'

            # Replace all <form ...> with <form ...>\n<input...>
            # but wait, some forms might just be <form>
            new_content = re.sub(r'<form\b[^>]*>', replacer, content, flags=re.IGNORECASE)
            
            # Since we could inject multiple times if run twice, let's just make sure we didn't double inject.
            # A simple way: remove existing tokens first, then inject.
            content_cleaned = re.sub(r'\n?\s*<input type="hidden" name="csrf_token" value="{{ csrf_token\(\) }}">\n?', '', content)
            
            new_content = re.sub(r'<form\b[^>]*>', replacer, content_cleaned, flags=re.IGNORECASE)

            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print('Updated form in ' + path)
