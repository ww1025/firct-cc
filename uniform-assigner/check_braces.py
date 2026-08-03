import requests, re
r = requests.get('http://localhost:8765/warehouse')
t = r.text

js_start = t.find('<script>')
js_end = t.find('</script>')
js = t[js_start:js_end]

# Find first few {{ occurrences
matches = [(m.start(), js[max(0,m.start()-10):m.end()+10]) for m in re.finditer(r'\{\{', js)]
print('First 5 {{ occurrences:')
for pos, ctx in matches[:5]:
    print('  pos={}: ...{}...'.format(pos, ctx))

matches2 = [(m.start(), js[max(0,m.start()-10):m.end()+10]) for m in re.finditer(r'\}\}', js)]
print('First 5 }} occurrences:')
for pos, ctx in matches2[:5]:
    print('  pos={}: ...{}...'.format(pos, ctx))

print('\nTotal {{ in JS: {}'.format(js.count('{{')))
print('Total }} in JS: {}'.format(js.count('}}')))
