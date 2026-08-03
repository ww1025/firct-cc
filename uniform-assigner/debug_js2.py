import requests, json

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Extract JS and try to find potential issues
s = html.find('<script>') + 8
e = html.find('</script>')
js = html[s:e]

# Check for problematic unescaped characters in the JS strings
# The emoji and Chinese chars in template strings should be fine
# But what about quotes inside attributes?

# Let's check buildBoots generated HTML more carefully
boots_start = js.find('function buildBoots(){')
boots = js[boots_start:]

# Check for backtick issues
print('backticks in buildBoots:', boots[:2000].count('`'))

# Check all quote patterns in the generated HTML
# The h variable uses single quotes, so any unescaped single quotes would break
# Let's find the h=' pattern and check if it's properly closed
import re
# Find all h='...' or h="..." patterns
for line_num, line in enumerate(boots[:2000].split('\n'), 1):
    if 'h=' in line or "h+=" in line:
        # Check if line ends with a semicolon or continuation
        print('Line {}: {} chars, ends with: {}'.format(line_num, len(line), repr(line[-20:])))

# Also check: the original page uses `<div class="section">`
# In the JS string, these double quotes inside single-quoted strings should be fine
# But let me check for any special issue with the `'` character
print('\n=== Checking for stray single quotes in buildBoots HTML string ===')
# Find the first h= line
first_h = re.search(r"h='[^']*'", boots)
if first_h:
    print('First h= assignment:', first_h.group()[:100])

# Check for the pattern: h+='...'+...+'...'
# These have multiple single-quoted strings concatenated - any mismatch?
h_plus_lines = re.findall(r"h\+='[^']*'", boots)
print('\nh+=\'...\' patterns (first 3):')
for line in h_plus_lines[:3]:
    print(' ', line[:120])

# Most importantly: check if the `'` character in class names like `class='section'`
# conflicts with the outer `h+='...'` string delimiter
# Wait, the JS uses single quotes for strings AND class attributes...
# Let me check more carefully
print('\n=== CHECK: single quotes in class names ===')
# In buildBoots: h+='<div class="section">...'
# Wait no - it should use double quotes for HTML attributes inside single-quoted JS strings
# Let me check what the actual JS has
has_double_quotes = 'class="section"' in boots
has_single_quotes_in_html = "class='section'" in boots
print('class="section" in buildBoots:', has_double_quotes)
print("class='section' in buildBoots:", has_single_quotes_in_html)
