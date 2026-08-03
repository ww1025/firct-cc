import io, os, base64, sys
sys.path.insert(0, '.')
import openpyxl
from server import parse_equipment_sheet, parse_shared_relations, merge_relations, detect_conflicts, build_pool, resolve, generate_excel, parse_schedule

excel_path = '本月礼服分配.xlsx'

# 柳洋 和 孙鸣 共用 M180/96-02 礼服 — 如果同一天出勤就会冲突
schedule_text = '周一：柳洋、孙鸣、马欣雅、张博宣'

schedule = parse_schedule(schedule_text)
print(f'Schedule: {schedule}')

wb = openpyxl.load_workbook(excel_path)
persons = parse_equipment_sheet(wb['装备分配'])

# 查两人的装备
for p in persons:
    if p['name'] in ('柳洋', '孙鸣'):
        print(f"  {p['name']}: uniform={p['uniform']}")

rels = parse_shared_relations(persons)
mrels = merge_relations(rels)
conflicts = detect_conflicts(schedule, mrels)
print(f'\nConflicts: {len(conflicts)}')
for c in conflicts:
    print(f'  {c}')

pool = build_pool(wb)
reassigns, changed = resolve(conflicts, persons, schedule, pool)
print(f'\nReassigns: {len(reassigns)}, Changed: {changed}')
for r in reassigns:
    print(f'  {r}')

b64 = generate_excel(excel_path, persons, schedule, changed)
out = base64.b64decode(b64)
with open('verify_debug.xlsx', 'wb') as f:
    f.write(out)
print('\nWrote verify_debug.xlsx')
print(f'Changed persons equipment:')
for name, ch in changed.items():
    p = next(x for x in persons if x['name'] == name)
    for t, new in ch.items():
        print(f'  {name}: {t} {p[t]} -> {new}')
