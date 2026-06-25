
import re

with open('app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check from PO Detail to User List
segment = lines[1021:1510]
stack = []

for i, line in enumerate(segment):
    line_num = i + 1022
    tags = re.findall(r'<(div|/div)', line)
    for tag in tags:
        if tag == 'div':
            stack.append((line_num, line.strip()))
        else:
            if not stack:
                print(f"[{line_num}] EXTRA </div>")
            else:
                l_start, content = stack.pop()

    if 1300 <= line_num <= 1315:
        print(f"[{line_num}] Stack: {[s[0] for s in stack]}")

if stack:
    print(f"Unclosed divs: {stack}")
else:
    print("Balanced")
