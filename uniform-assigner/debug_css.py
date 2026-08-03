import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

# Extract complete CSS + HTML before <script>
script_pos = html.find('<script>')
pre_js = html[:script_pos]

# Check the end of CSS - last 200 chars before <script>
print('=== Last 300 chars of HTML/CSS before <script> ===')
print(pre_js[-300:])
print()

# Check the section class - does it have the gold left border?
if '.section{' in html:
    idx = html.find('.section{')
    print('=== Section CSS ===')
    print(html[idx:idx+300])
