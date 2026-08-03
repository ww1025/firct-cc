import io, os, re, base64, tempfile, sys
sys.path.insert(0, '.')
import openpyxl
from difflib import SequenceMatcher as SM

# Manually run the business logic to debug
from server import parse_equipment_sheet, parse_shared_relations, merge_relations, detect_conflicts, build_pool, resolve, generate_excel, parse_schedule

excel_path = '本月礼服分配.xlsx'
schedule_text = '周一：柳洋、姚忻成、马欣雅、张博宣'

schedule = parse_schedule(schedule_text)
print(f'Schedule: {schedule}')

wb = openpyxl.load_workbook(excel_path)
print(f'Sheets: {wb.sheetnames}')

persons = parse_equipment_sheet(wb['装备分配'])
print(f'Persons count: {len(persons)}')
print(f'First 5: {[(p["name"], p["uniform"], p["note"]) for p in persons[:5]]}')

rels = parse_shared_relations(persons)
print(f'Raw relations: {len(rels)}')
for r in rels:
    print(f'  {r}')

mrels = merge_relations(rels)
print(f'Merged relations: {len(mrels)}')
for r in mrels:
    print(f'  {r}')

conflicts = detect_conflicts(schedule, mrels)
print(f'Conflicts: {len(conflicts)}')
for c in conflicts:
    print(f'  {c}')

pool = build_pool(wb)
print(f'Pool: {len(pool["uniform"])} uniforms, {len(pool["hat"])} hats')

reassigns, changed = resolve(conflicts, persons, schedule, pool)
print(f'Reassigns: {len(reassigns)}, Changed: {changed}')
for r in reassigns:
    print(f'  {r}')

b64 = generate_excel(excel_path, persons, changed)
print(f'Base64 length: {len(b64)}')

# Save output to verify
out = base64.b64decode(b64)
with open('debug_output.xlsx', 'wb') as f:
    f.write(out)
print('Written to debug_output.xlsx')
