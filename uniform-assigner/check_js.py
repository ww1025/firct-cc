import requests, re
r = requests.get('http://localhost:8765/warehouse')
t = r.text
dbs = re.findall(r'(\{\{|\}\})', t)
print('Double braces remaining:', len(dbs))
checks = [
    'var D = ',
    'var ALL=[]',
    'function init()',
    'function buildBoots()',
    'function buildSec(',
    'function indexDOM()',
    'function indexAll()',
    'function fmtName(',
    'function si()',
    'function ds()',
    'openPanel(',
    'closePanel(',
    'clearHL(',
    '</script>',
]
for c in checks:
    ok = c in t
    print(f'  [{"OK" if ok else "MISSING"}] {c[:45]}')
print('Total size:', len(t), 'chars')
