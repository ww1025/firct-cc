import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

# Find the HOME_HTML section
idx = content.find('HOME_HTML')
print(f'HOME_HTML at byte {idx}')

# Find lines around 880-895
lines = content.split('\n')
for i in range(878, 898):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i][:100])}')
