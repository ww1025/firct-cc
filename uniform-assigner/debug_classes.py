import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Check section CSS - it says `section{` not `.section{`
sec_css = html.find('.section{margin')
print('Section CSS with dot:', sec_css > 0)

# Now check buildBoots output - it generates div with class="section"
js_start = html.find('function buildBoots(){')
# Find the first h+= that generates section div
idx = html.find('class="section"', js_start)
print('buildBoots uses class="section":', idx > 0)
if idx > 0:
    print('Context:', html[idx-50:idx+60])

# Check buildSec for section class too
sec_idx = html.find("function buildSec(")
print('\nbuildSec starts at:', sec_idx)
# Find class="section" in buildSec
for m in [('class="section"', html.find('class="section"', sec_idx, sec_idx+5000))]:
    print('  buildSec section class found:', m[1] > 0)
    if m[1] > 0:
        print('  Context:', html[m[1]-30:m[1]+60])

# The real question: does the CSS have .section (with dot)?
# Let me look more carefully
print('\n=== Looking for .section in CSS ===')
style_start = html.find('<style>')
style_end = html.find('</style>')
css = html[style_start:style_end]
# Find all occurrences of "section" in CSS
import re
for m in re.finditer(r'\.?section[^{]*\{', css):
    start = max(0, m.start()-10)
    end = m.end()
    print('  ', css[start:end])
