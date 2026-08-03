import requests

r = requests.get('http://localhost:8765/warehouse')
html = r.text

js_start = html.find('function init(){')
js_end = html.find('function buildBoots(){')
init_fn = html[js_start:js_end]
print('Init function:')
print(init_fn)
print()

boots_start = html.find('function buildBoots(){')
boots_end = html.find('function buildSec(')
boots_fn = html[boots_start:boots_end]
print('buildBoots function (first 500 chars):')
print(boots_fn[:500])
print()

# Check if there's a problematic closing brace pattern
import re
# Look for the pattern }} that survived in the JS data
data_start = html.find('var D = {')
data_end = html.find('var ALL=[]')
data_block = html[data_start:data_end]
print('Data block size:', len(data_block))
print('Double braces in data:', data_block.count('{{'))
print('Double close braces in data:', data_block.count('}}'))

# Print the transition from data to functions
trans = html[data_end-50:data_end+100]
print('\nData→ALL transition:')
print(trans)
