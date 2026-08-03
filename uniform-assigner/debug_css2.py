import requests, re

r = requests.get('http://localhost:8765/warehouse')
html = r.text
css_start = html.find('<style>') + 7
css_end = html.find('</style>')
css = html[css_start:css_end]

# Track brace balance
lines = css.split('\n')
balance = 0
for i, line in enumerate(lines, 1):
    balance += line.count('{') - line.count('}')
    if balance < 0:
        print('NEGATIVE balance at line {}: balance={}'.format(i, balance))
        print('  Line:', line[:120])
    # Print every line where balance changes
    if line.count('{') != line.count('}'):
        bal = line.count('{') - line.count('}')
        print('  L{} [bal: {:+d} → {}]: {}'.format(i, bal, balance, line.strip()[:120]))

print('\nFinal balance:', balance)

# Find the exact location of the extra }
for i in range(len(css)):
    if css[i] == '}':
        # Check if we have an extra at this position
        before = css[:i+1]
        if before.count('{') < before.count('}'):
            ctx = css[max(0,i-50):i+20]
            print('\nExtra }} at pos {}: ...{}...'.format(i, ctx))
            break
