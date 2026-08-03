import requests

# Write the full page to a file so user can open it locally
r = requests.get('http://localhost:8765/warehouse')
with open(r'C:\Users\夏瑞泽\Desktop\firct cc\warehouse_test.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print('Written to warehouse_test.html, size:', len(r.text))

# Also verify the init() call works in a simple test
# The init function: function init(){var h=buildBoots()+buildSec(D.belts,'belt','🎽 腰带','#C62828')+buildSec(D.uniforms,'uniform','👔 礼服','#1565C0');document.getElementById('ct').innerHTML=h;indexDOM();indexAll()}
# Check document.getElementById('ct') - ct element must exist before init()
ct_pos = r.text.find('id="ct"')
print('ct div position:', ct_pos)
# Is ct BEFORE the script?
script_pos = r.text.find('<script>')
print('script position:', script_pos)
print('ct before script:', ct_pos < script_pos)  # MUST be True

# Check: is the script at the end of body?
body_end = r.text.find('</body>')
print('</body> position:', body_end)
print('</script> position:', r.text.find('</script>'))

# Verify all D data is parseable
js_start = r.text.find('<script>') + 8
js_end = r.text.find('</script>')
js = r.text[js_start:js_end]

# Quick check: does the D variable parse as valid JSON?
# Extract the JSON part
d_start = js.find('var D = ') + 8
d_end = js.find(';\nvar ALL=[]')
d_json = js[d_start:d_end]
print('\nJSON check:')
print('  D starts with:', d_json[:50])
print('  D ends with:', d_json[-30:])
# Count braces
print('  Open braces:', d_json.count('{'))
print('  Close braces:', d_json.count('}'))
