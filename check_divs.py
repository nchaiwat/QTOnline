
import re

with open('app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

segment = lines[1021:1446] # 1022 to 1446 (0-indexed)
stack = []

for i, line in enumerate(segment):
    line_num = i + 1022
    # Find all start tags and end tags in order
    tags = re.findall(r'<(div|/div)', line)
    for tag in tags:
        if tag == 'div':
            stack.append(line_num)
        else:
            if not stack:
                print(f"Extra </div> at line {line_num}")
            else:
                stack.pop()

if stack:
    print(f"Unclosed divs from lines: {stack}")
else:
    print("Balanced (within segment)")
