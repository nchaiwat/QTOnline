
import re

with open('app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check from start to User List Page
segment = lines[0:1502]
stack = []

for i, line in enumerate(segment):
    line_num = i + 1
    # Find all start tags and end tags in order
    tags = re.findall(r'<(div|/div)', line)
    for tag in tags:
        if tag == 'div':
            stack.append((line_num, line.strip()))
        else:
            if not stack:
                print(f"Extra </div> at line {line_num}")
            else:
                l_start, content = stack.pop()
                if l_start < 1447 and line_num >= 1448:
                     pass # Normal
                # Debug specific range
                if 1440 <= line_num <= 1446:
                    print(f"Line {line_num} closes Line {l_start}: {content}")

if stack:
    print(f"Unclosed divs at end of segment:")
    for ln, content in stack:
        print(f"Line {ln}: {content}")
