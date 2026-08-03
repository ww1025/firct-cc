import requests

h = requests.get('http://localhost:8765').text
wh = requests.get('http://localhost:8765/warehouse').text
fac = requests.get('http://localhost:8765/faculty').text

js_start = wh.find('<script>')
js_end = wh.find('</script>')
js = wh[js_start:js_end]

results = [
    ('HOME: flag-red', '#B81616' in h),
    ('HOME: 2 cards', h.count('class="card"') == 2),
    ('HOME: warehouse link', '/warehouse' in h),
    ('HOME: fadeInUp', 'fadeInUp' in h),
    ('WAREHOUSE: JS no double braces', '{{' not in js),
    ('WAREHOUSE: var D correct', '"grid"' in js),
    ('WAREHOUSE: buildBoots', 'buildBoots' in wh),
    ('WAREHOUSE: data X44-05', 'X44-05' in wh),
    ('WAREHOUSE: back link', '返回首页' in wh),
    ('WAREHOUSE: footer star', 'footer-star' in wh),
    ('WAREHOUSE: section cards', wh.count('class="section"') == 3),
    ('FACULTY: still works', '院系升旗' in fac),
]

for name, ok in results:
    status = "OK" if ok else "FAIL"
    print('  [{}] {}'.format(status, name))
