import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

# Remove DAILY_HTML entirely
idx1 = content.find("DAILY_HTML = r'''")
idx2 = content.find("HOME_HTML = r'''")

if idx1 > 0 and idx2 > 0:
    # Find the triple-quote end of DAILY_HTML (it ends with </html>''')
    end_marker = "</html>'''"
    idx_end = content.find(end_marker, idx1)
    if idx_end > 0:
        idx_end += len(end_marker)
        # Remove DAILY_HTML section
        content = content[:idx1] + content[idx2:]
        print(f"Removed DAILY_HTML ({idx_end - idx1} bytes)")

# Remove /daily route
old_route = """@app.route('/daily')
def daily():
    return DAILY_HTML

"""
content = content.replace(old_route, "")

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'w', encoding='utf-8') as f:
    f.write(content)
print("Done - DAILY_HTML and /daily route removed")
