
import re

with open('app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check whole file
stack = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Find all divs, but ignore them if they are in comments or scripts?
    # Actually, let's just use a better regex that handles multiple tags on one line
    matches = re.finditer(r'<(div|/div)', line)
    for m in matches:
        tag = m.group(1)
        if tag == 'div':
            stack.append(line_num)
        else:
            if not stack:
                print(f"Extra </div> at line {line_num}")
            else:
                stack.pop()

if stack:
    print(f"Unclosed divs at end of file: {stack}")
else:
    print("File is balanced")
