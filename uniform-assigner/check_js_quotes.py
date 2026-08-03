import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Extract JUST the JS
s = html.find('<script>') + 8
e = html.find('</script>')
js = html[s:e]

# Write JS to a file
with open(r'C:\Users\夏瑞泽\Desktop\firct cc\warehouse_js.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('Written, size:', len(js))

# Now parse through to find any template string issues
# The key issue might be in how the HTML strings are constructed
# Look for lines with h+='...' and check quote matching

import re
lines = js.split('\n')
for i, line in enumerate(lines):
    stripped = line.strip()
    # Check lines that start with h+=' or h='
    if stripped.startswith("h+='") or stripped.startswith("h='"):
        # Count single quotes
        sq = stripped.count("'")
        if sq % 2 != 0 and not stripped.endswith("'"):
            pass  # continuation lines are OK
        elif sq % 2 != 0:
            print('WARN Line {} (odd quotes): {}'.format(i+1, stripped[:100]))

# Also look for the specific buildSec function
buildsec_start = js.find('function buildSec(')
print('\nbuildSec found at char', buildsec_start)
if buildsec_start > 0:
    # Show the first few lines
    chunk = js[buildsec_start:buildsec_start+600]
    print(chunk)
