with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the problematic region and fix indentation
# Line 973 (0-indexed: 972) has extra indent
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this line has indent 24 where it should be 20 (inside try block)
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    # Lines 973-1028 (0-idx 972-1027) need to be fixed: reduce 4 spaces
    # The try block at line 967 (0-idx 966) has body at 16, but the lines after 972 are at 24
    # They should be at 20 (inside try -> should be 16, not 20... let me think)
    # The structure should be:
    # with st.status(..."):   -> 12 spaces
    #     queue_names = ...    -> 16 spaces
    #     with NTF as t:       -> 16 spaces
    #         t.write(...)     -> 20 spaces
    #     try:                 -> 16 spaces
    #         wb = ...         -> 20 spaces
    #         ...              -> 20 spaces
    #
    # Currently lines 973+ are at 24 spaces. They should be at 20.

    if 972 <= i <= 1027 and indent >= 24:
        # Reduce by exactly 4 spaces
        fixed_lines.append(' ' * (indent - 4) + stripped + '\n')
    else:
        fixed_lines.append(line)
    i += 1

with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)
print('Fix applied to lines 973-1028')
