import requests
r = requests.get('http://localhost:8765')
h = r.text
wh = requests.get('http://localhost:8765/warehouse').text
fac = requests.get('http://localhost:8765/faculty').text

checks = [
    ('HOME: flag-red', '#B81616' in h),
    ('HOME: 物资仓库 card', '物资仓库' in h),
    ('HOME: two card links', h.count('class="card"') == 2),
    ('HOME: fadeInUp', 'fadeInUp' in h),
    ('WAREHOUSE: buildBoots', 'buildBoots' in wh),
    ('WAREHOUSE: flag-red', '#B81616' in wh),
    ('WAREHOUSE: back link', '返回首页' in wh),
    ('WAREHOUSE: footer star', 'footer-star' in wh),
    ('WAREHOUSE: grid-template', 'grid-template-columns' in wh),
    ('WAREHOUSE: boots data X44-05', 'X44-05' in wh),
    ('WAREHOUSE: belts data', '"belts"' in wh),
    ('WAREHOUSE: uniforms data', '"uniforms"' in wh),
    ('FACULTY: still works', '院系升旗' in fac),
]
for name, ok in checks:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
