import os
import subprocess

# 1. Modify pyproject.toml
with open('pyproject.toml', 'r') as f:
    content = f.read()

content = content.replace('version = "2.0.0rc4"\n', 'dynamic = ["version"]\n')
if '[tool.setuptools.dynamic]' not in content:
    content += '\n[tool.setuptools.dynamic]\nversion = {attr = "betterleaks.__version__"}\n'

if 'Issues = ' not in content:
    content = content.replace(
        'Repository = "https://github.com/as1605/betterleaks-py"\n',
        'Repository = "https://github.com/as1605/betterleaks-py"\nIssues = "https://github.com/as1605/betterleaks-py/issues"\nChangelog = "https://github.com/as1605/betterleaks-py/releases"\n'
    )

with open('pyproject.toml', 'w') as f:
    f.write(content)

# 2. Modify setup.py
with open('setup.py', 'r') as f:
    content = f.read()

content = content.replace('    import ssl\n', '')
content = content.replace(
    '        ctx = ssl.create_default_context()\n'
    '        ctx.check_hostname = False\n'
    '        ctx.verify_mode = ssl.CERT_NONE\n'
    '        \n',
    ''
)
content = content.replace('context=ctx', 'timeout=30')
content = content.replace('"*.h",', '"*.h",\n            "py.typed",')

with open('setup.py', 'w') as f:
    f.write(content)

# 3. Create py.typed
os.makedirs('src/betterleaks', exist_ok=True)
with open('src/betterleaks/py.typed', 'w') as f:
    f.write('')

print("Fixes applied.")
