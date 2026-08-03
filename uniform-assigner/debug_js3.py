import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Write it to a file so I can check more carefully
with open(r'C:\Users\夏瑞泽\Desktop\firct cc\warehouse_full.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Extract JS
s = html.find('<script>') + 8
e = html.find('</script>')
js = html[s:e]

# Write JS to separate file for syntax check
with open(r'C:\Users\夏瑞泽\Desktop\firct cc\warehouse_js.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('HTML saved:', len(html), 'chars')
print('JS saved:', len(js), 'chars')

# Try to parse JS with Node in a sandbox way - just check for obvious issues
# Check for problematic patterns
import re

# Check balance of all brace types
for c in ['{', '}', '(', ')', '[', ']']:
    count = js.count(c)
    print('  {}: {}'.format(c, count))

# Check for any line with mismatched quotes
lines = js.split('\n')
for i, line in enumerate(lines):
    # Count single quotes (rough check)
    sq = line.count("'")
    if sq % 2 != 0:
        # This line might be split across lines - check more carefully
        # Exclude lines with escaped quotes in template strings
        if "\\'" not in line and "```" not in line:
            # This is fine if it's part of a concatenation like h+='...'+
            if line.strip().endswith('+') or line.strip().startswith('+'):
                continue
            if 'h+=' in line:
                continue
            print('Odd quotes line {}: {}'.format(i+1, line[:120]))

# Check for unclosed template literal (backtick)
backtick_count = js.count('`')
print('\nBackticks:', backtick_count, '(should be even:', backtick_count % 2 == 0, ')')
