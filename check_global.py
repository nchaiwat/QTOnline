
import re

with open('app.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Find all div tags with their positions
matches = re.finditer(r'<(div|/div)', text)
stack = []

for m in matches:
    tag = m.group(1)
    pos = m.start()
    line_num = text.count('\n', 0, pos) + 1
    
    if tag == 'div':
        stack.append(line_num)
    else:
        if not stack:
            print(f"Extra </div> at line {line_num}")
        else:
            stack.pop()

if stack:
    # print(f"Unclosed divs at end: {stack}")
    pass
