import requests, re

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Find body between <body> and <script>
body_end = html.find('<script>')
body = html[:body_end]

# Check key elements
for tag in ['id="ct"', 'id="q"', 'id="sug"', 'id="ov"', 'id="pn"', 'id="pt"', 'id="pb"']:
    print('  {} {}'.format('✓' if tag in body else '✗', tag))

# Check CSS - are key styles present?
for css in ['section{', '.section-header', '.cell{', '.cell.boot', '.cell.belt', '.cell.uniform', '.panel', '.overlay']:
    print('  CSS {}: {}'.format(css, '✓' if css in html else '✗'))

# Extract and check JS for obvious syntax errors
js_start = html.find('<script>') + 8
js_end = html.find('</script>')
js = html[js_start:js_end]

# Check if init() is the last thing
last_line = js.strip().split('\n')[-1]
print('\nLast JS line:', last_line[:100])

# Check for any {{ or }} that survived
if '{{' in js:
    print('\nWARNING: {{ found in JS!')
    for m in re.finditer(r'\{\{', js):
        ctx = js[m.start()-5:m.start()+15]
        print('  ', ctx)
