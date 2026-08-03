import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

js_start = html.find('<script>')
js_end = html.find('</script>')
js = html[js_start + 8:js_end]

with open(r'C:\Users\夏瑞泽\Desktop\firct cc\warehouse_js_debug.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('JS length:', len(js))
print('First 200 chars:')
print(js[:200])
print()
print('Last 100 chars:')
print(js[-100:])
print()

# Check for basic JS structure
checks = ['var D = ', 'var ALL', 'function init', 'function buildBoots', 'function buildSec',
          'function indexDOM', 'function indexAll', 'function fmtName',
          'function openPanel', 'function closePanel', 'function si', 'function ds', 'init()']
for c in checks:
    print('  {} {}'.format('✓' if c in js else '✗', c))
