import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

# Find WAREHOUSE_HTML section
start = content.find("WAREHOUSE_HTML = r'''")
end = content.find("\n# ── Routes ──", start)

warehouse = content[start:end]

# Replace double braces with single braces
fixed = warehouse.replace('{{', '{').replace('}}', '}')

# Handle edge case: JSON string "belts" and "uniforms" — after replacement,
# the escaped double-braces in the JSON data should now be correct single braces
# But check: the data string had \"belts\" etc. — those were fine
# The JavaScript template strings with ${} should be fine too

content = content[:start] + fixed + content[end:]

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed double braces in WAREHOUSE_HTML")
