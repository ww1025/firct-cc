import requests
r = requests.get('http://localhost:8765')
r2 = requests.get('http://localhost:8765/faculty')

print('=== HOME ===')
for name, ok in [
    ('Flag red #B81616', '#B81616' in r.text),
    ('Gold stars #F5C518', '#F5C518' in r.text),
    ('Cream BG #F5F1E6', '#F5F1E6' in r.text),
    ('fadeInUp animation', 'fadeInUp' in r.text),
    ('Card hover lift', 'translateY(-4px)' in r.text),
    ('Gold left border', 'border-left:3px solid var(--gold)' in r.text),
    ('Footer stars', 'footer-star' in r.text),
]:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')

print()
print('=== FACULTY ===')
for name, ok in [
    ('Flag red header', '#B81616' in r2.text),
    ('Red badge BG', 'background:var(--flag-red)' in r2.text),
    ('Red button CSS', 'btn-b' in r2.text and 'var(--flag-red)' in r2.text),
    ('Red corner brackets', 'var(--flag-red)' in r2.text),
    ('Gold spinner', '#F5C518' in r2.text),
    ('Card fadeInUp', 'fadeInUp' in r2.text),
    ('Footer stars', 'footer-star' in r2.text),
]:
    print(f'  [{"OK" if ok else "FAIL"}] {name}')
