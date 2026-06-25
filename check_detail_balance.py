
import re

with open('app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check from PO Detail to User List
segment = lines[1021:1448]
stack = []

for i, line in enumerate(segment):
    line_num = i + 1022
    tags = re.findall(r'<(div|/div)', line)
    for tag in tags:
        if tag == 'div':
            stack.append(line_num)
        else:
            if not stack:
                print(f"[{line_num}] Extra </div>")
            else:
                l_start = stack.pop()
                # print(f"[{line_num}] Closest <div> from line {l_start}")

if stack:
    print(f"Unclosed divs at line 1448: {stack}")
else:
    print("Balanced reached at line 1448")
