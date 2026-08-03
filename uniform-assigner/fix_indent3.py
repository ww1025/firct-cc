with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix ALL remaining over-indented lines in the faculty block
# Lines that start with 24 spaces should be reduced to 20 spaces (inside try block)
import re

lines = text.split('\n')
fixed = []
for line in lines:
    if line.startswith('                    ') and not line.startswith('                        '):
        # 20 spaces -> reduce to 16
        line = '                ' + line[20:]
    elif line.startswith('                        '):
        # 24 spaces -> reduce to 20
        line = '                    ' + line[24:]
    elif line.startswith('                            '):
        # 28 spaces -> reduce to 24
        line = '                        ' + line[28:]
    elif line.startswith('                                    '):
        # 36 spaces -> reduce to 32
        line = '                                ' + line[36:]
    fixed.append(line)

text = '\n'.join(fixed)
with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done')
