import requests
r = requests.get('http://localhost:8765/warehouse')
t = r.text

# Check for double braces in the actual HTML output
import re
# Find <script> section
s = t.find('<script>')
e = t.find('</script>')
js = t[s:e]

# Look for double open braces
open_braces = [m.start() for m in re.finditer(r'\{\{', js)]
close_braces = [m.start() for m in re.finditer(r'\}\}', js)]
print("Double {{ in JS:", len(open_braces))
print("Double }} in JS:", len(close_braces))

if open_braces:
    print("\nSample {{ context:")
    for pos in open_braces[:3]:
        ctx = js[max(0,pos-15):pos+20]
        print("  ...{}...".format(ctx.replace('\n',' ')))
if close_braces:
    print("\nSample }} context:")
    for pos in close_braces[:3]:
        ctx = js[max(0,pos-15):pos+20]
        print("  ...{}...".format(ctx.replace('\n',' ')))
