"""
浙江大学国旗仪仗队 —— Streamlit Cloud 部署版
首页 + 院系礼服分配 + 物资仓库
"""
import streamlit as st
import base64, io, os, re, tempfile, math
from difflib import SequenceMatcher
import openpyxl
from openpyxl.styles import PatternFill
from PIL import Image
import numpy as np

st.set_page_config(page_title="浙江大学国旗仪仗队", page_icon="🇨🇳", layout="wide", initial_sidebar_state="collapsed")

# ── CSS 注入 ──
def inject_css():
    st.markdown("""
    <style>
    #MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden}
    .stApp {background-color: #F5F1E6}
    .block-container {padding-top: 0 !important; padding-bottom: 0 !important}
    section.main {padding: 0 !important}
    </style>
    """, unsafe_allow_html=True)

# ── 国旗红样式 ──
FLAG_STYLE = """
<style>
.flag-header {
    background: #B81616; color: #fff; padding: 20px 32px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid rgba(245,197,24,.3);
    margin: -1rem -1rem 2rem -1rem;
}
.flag-header h1 {font-family: 'SimSun','KaiTi',serif; font-size: 18px; font-weight: 700; letter-spacing: .08em; color: #fff; margin: 0}
.flag-header .star {color: #F5C518; font-size: 16px}
.flag-footer {
    text-align: center; padding: 28px; color: #1a3a2a;
    font-family: 'SimSun','KaiTi',serif; font-size: 12px;
    letter-spacing: .06em; border-top: 1px solid rgba(184,22,22,.08);
    margin: 3rem 0 0 0;
}
.flag-footer .star {color: #F5C518; font-size: 10px; margin: 0 6px}
</style>
"""

# ── 业务逻辑 ──
YELLOW = 'FFFFFF00'

@st.cache_resource
def get_ocr_reader():
    import easyocr
    return easyocr.Reader(['ch_sim'], gpu=False)

def fuzzy_match(ocr_name, known_names):
    if not known_names: return ocr_name
    if ocr_name in known_names: return ocr_name
    cleaned = re.sub(r'[_|^~\s\d]+', '', ocr_name)
    if cleaned in known_names: return cleaned
    for ref in known_names:
        if len(ref) >= 2 and len(cleaned) >= 2 and cleaned[:2] == ref[:2]: return ref
    best, best_score = None, 0
    for ref in known_names:
        common = len(set(cleaned) & set(ref))
        ratio = SequenceMatcher(None, cleaned, ref).ratio()
        score = common * 3 + ratio * 5
        if score > best_score: best_score, best = score, ref
    return best if best and best_score >= 6 else re.sub(r'[_|^~\s\d]+', '', ocr_name)

def fuzzy_match_aggressive(ocr_name, known_names):
    if not ocr_name or not known_names: return None
    if ocr_name in known_names: return ocr_name
    cleaned = re.sub(r'[_|^~\s\d\s]+', '', ocr_name)
    if not cleaned: return None
    if cleaned in known_names: return cleaned
    candidates = [r for r in known_names if len(r) >= 2 and len(cleaned) >= 2 and cleaned[:2] == r[:2]]
    if candidates: return min(candidates, key=len)
    best, best_score = None, 0
    cc = set(cleaned)
    for ref in known_names:
        rc = set(ref); common = len(cc & rc)
        if common == 0: continue
        overlap = common / max(len(cc), len(rc))
        score = overlap * 10 - abs(len(ref) - len(cleaned)) * 1.5
        if score > best_score: best_score, best = score, ref
    return best if best and best_score >= 2.0 else None

def force_correct_name(ocr_text, known_names):
    if not ocr_text or len(ocr_text) < 2: return None
    if ocr_text in known_names: return ocr_text
    cleaned = re.sub(r'[_|^~\s\d]+', '', ocr_text)
    if cleaned in known_names: return cleaned
    candidates = [r for r in known_names if len(r) >= 2 and len(cleaned) >= 2 and cleaned[:2] == r[:2]]
    if candidates: return min(candidates, key=len)
    best, best_score = None, 0
    nc = set(cleaned)
    for ref in known_names:
        rc = set(ref); common = len(nc & rc)
        overlap = common / max(len(nc), len(rc), 1)
        seq = SequenceMatcher(None, cleaned, ref).ratio()
        score = overlap * 10 + seq * 5
        if score > best_score: best_score, best = score, ref
    return best if best and best_score >= 5 else None

def parse_equipment_sheet(ws):
    persons = []
    for row in range(2, ws.max_row+1):
        name = ws.cell(row=row, column=2).value
        if not name: continue
        name = str(name).strip()
        uni = str(ws.cell(row=row, column=3).value or '').strip()
        hat = str(ws.cell(row=row, column=4).value or '').strip()
        boots = str(ws.cell(row=row, column=5).value or '').strip()
        belt = str(ws.cell(row=row, column=6).value or '').strip()
        note = str(ws.cell(row=row, column=7).value or '').strip()
        persons.append(dict(name=name, gender='M' if uni.startswith('M') else 'F',
                            uniform=uni, hat=hat, boots=boots, belt=belt, note=note))
    return persons

def parse_shared_relations(persons):
    rels, seen = [], set()
    for p in persons:
        if not p['note']: continue
        for seg in re.split(r'[，；]', p['note']):
            seg = seg.strip()
            if not seg.startswith('和'): continue
            idx = seg.find('共用')
            if idx < 0: continue
            names = [n.strip() for n in re.split(r'[、，, ]+', seg[1:idx]) if n.strip()]
            after = seg[idx+2:]
            types = [t for t in [('uniform','礼服'),('hat','礼帽'),('boots','马靴'),('belt','腰带')] if t[1] in after]
            for n in names:
                for t, _ in types:
                    code = p[t]
                    key = f"{t}|{code}|{','.join(sorted([p['name'], n]))}"
                    if key not in seen:
                        seen.add(key)
                        rels.append(dict(item_code=code, item_type=t, shared_by=[p['name'], n]))
    return rels

def merge_relations(rels):
    m = {}
    for r in rels:
        k = f"{r['item_type']}|{r['item_code']}"
        m.setdefault(k, set()).update(r['shared_by'])
    return [dict(item_code=k.split('|')[1], item_type=k.split('|')[0], shared_by=list(v)) for k, v in m.items()]

def detect_conflicts(schedule, rels):
    conflicts = []
    for day in schedule:
        daily = set(day['people'])
        for r in rels:
            overlap = [p for p in r['shared_by'] if p in daily]
            if len(overlap) >= 2:
                for i in range(1, len(overlap)):
                    conflicts.append(dict(day=day['day'], item_type=r['item_type'], item_code=r['item_code'],
                                          person_to_move=overlap[i], person_to_keep=overlap[0]))
    return conflicts

def parse_uniform_code(code):
    m = re.match(r'^([FM])(\d+)/(\d+)-(\d+)$', code)
    return dict(gender=m.group(1), height=int(m.group(2)), chest=int(m.group(3))) if m else None

def parse_hat_code(code):
    m = re.match(r'^([FM])(\d{4})$', code)
    return dict(gender=m.group(1), number=int(m.group(2))) if m else None

def find_alternative(person, item_type, used_items, all_items):
    own = person[item_type]
    available = [x for x in all_items if x not in used_items and x != own]
    gender = person['gender']
    candidates = []
    for item in available:
        if item_type == 'uniform':
            info = parse_uniform_code(item)
            if not info or info['gender'] != gender: continue
            pi = parse_uniform_code(own) or dict(height=0, chest=0)
            score = abs(info['height'] - pi['height']) * 4 + abs(info['chest'] - pi['chest']) * 5
            candidates.append((score, item))
        elif item_type == 'hat':
            info = parse_hat_code(item)
            if not info or info['gender'] != gender: continue
            pi = parse_hat_code(own) or dict(number=0)
            candidates.append((abs(info['number'] - pi['number']), item))
        else:
            if item.startswith(gender): candidates.append((0, item))
    if not candidates:
        for item in available: candidates.append((999998, item))
    if not candidates:
        candidates = [(999999, x) for x in all_items if x.startswith(gender)]
    candidates.sort()
    return candidates[0][1] if candidates else None

def build_pool(wb):
    pool = dict(uniform=set(), hat=set())
    for row in range(2, wb['装备分配'].max_row+1):
        for col, key in [(3,'uniform'),(4,'hat')]:
            v = str(wb['装备分配'].cell(row=row, column=col).value or '').strip()
            if v: pool[key].add(v)
    for sn in ['礼服腰带摆放','礼帽摆放']:
        if sn in wb.sheetnames:
            ws = wb[sn]
            for row in range(3, ws.max_row+1):
                for col in range(1, ws.max_column+1):
                    v = str(ws.cell(row=row, column=col).value or '').strip()
                    if re.match(r'^[FM]\d{2,3}/', v): pool['uniform'].add(v)
                    if re.match(r'^[FM]\d{4}$', v): pool['hat'].add(v)
    return pool

def resolve(conflicts, persons, schedule, pool):
    reassigns, changed = [], {}
    by_day = {}
    for c in conflicts: by_day.setdefault(c['day'], []).append(c)
    for day, clist in by_day.items():
        people = next((set(s['people']) for s in schedule if s['day'] == day), set())
        used = {
            'uniform': {p['uniform'] for p in persons if p['name'] in people},
            'hat': {p['hat'] for p in persons if p['name'] in people}
        }
        for c in clist:
            person = next((p for p in persons if p['name'] == c['person_to_move']), None)
            if not person: continue
            t = c['item_type']
            alt = find_alternative(person, t, used[t], pool.get(t, set()))
            if alt:
                used[t].discard(person[t]); used[t].add(alt)
                reassigns.append(dict(person=person['name'], item_type=t, old_item=person[t], new_item=alt))
                changed.setdefault(person['name'], {})[t] = alt
                person[t] = alt
    return reassigns, changed

def generate_excel(template_path, persons, changed):
    wb = openpyxl.load_workbook(template_path)
    ws = wb['装备分配']
    name_map = {p['name']: p for p in persons}
    for row in range(2, ws.max_row+1):
        name = ws.cell(row=row, column=2).value
        if not name: continue
        name = str(name).strip()
        p = name_map.get(name)
        if not p: continue
        ch = changed.get(name, {})
        for col, key in [(3,'uniform'),(4,'hat'),(5,'boots'),(6,'belt'),(7,'note')]:
            cell = ws.cell(row=row, column=col)
            cell.value = p.get(key, '') or None
            if key in ch:
                cell.fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def parse_schedule(text):
    schedule = []
    day_patterns = [
        (r'周\s*一', '周一'), (r'周\s*二', '周二'),
        (r'周\s*三', '周三'), (r'周\s*四', '周四'), (r'周\s*五', '周五'),
    ]
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line: continue
        day = None
        for pat, label in day_patterns:
            if re.search(pat, line): day = label; break
        if not day: continue
        rest = re.sub(r'周\s*[一二三四五]\s*[:：]?\s*', '', line)
        chunks = re.split(r'[、，,]', rest)
        names = []
        for chunk in chunks:
            n = re.sub(r'\s+', '', chunk)
            if len(n) >= 2: names.append(n)
        if names: schedule.append(dict(day=day, people=names))
    return schedule

# ── 院系相关 ──
def uniform_sort_key(person):
    suit = person.get('uniform', '')
    if not suit: return (2, 999, 999, 999)
    gender_code = 0 if suit.startswith('F') else 1
    nums = [int(n) for n in re.findall(r'\d+', suit)]
    while len(nums) < 3: nums.append(0)
    return (gender_code, nums[0], nums[1], nums[2])

def sort_people_by_uniform(people):
    return sorted(people, key=uniform_sort_key)

def detect_faculty_conflicts(persons):
    conflicts = []
    for eq_type in ['uniform', 'hat', 'boots', 'belt']:
        eq_map = {}
        for p in persons:
            code = p.get(eq_type, '')
            if not code: continue
            eq_map.setdefault(code, []).append(p['name'])
        for code, names in eq_map.items():
            if len(names) >= 2:
                for i in range(1, len(names)):
                    conflicts.append(dict(item_type=eq_type, item_code=code, person_to_move=names[i], person_to_keep=names[0]))
    return conflicts

def resolve_faculty_conflicts(conflicts, persons, pool):
    reassigns, changed = [], {}
    used = {}
    for eq_type in ['uniform', 'hat', 'boots', 'belt']:
        used[eq_type] = {p.get(eq_type, '') for p in persons if p.get(eq_type)}
    for c in conflicts:
        person = next((p for p in persons if p['name'] == c['person_to_move']), None)
        if not person: continue
        t = c['item_type']
        alt = find_alternative(person, t, used[t], pool.get(t, set()))
        if alt:
            used[t].discard(person[t]); used[t].add(alt)
            reassigns.append(dict(person=person['name'], item_type=t, old_item=person[t], new_item=alt))
            changed.setdefault(person['name'], {})[t] = alt
            person[t] = alt
    return reassigns, changed

FACULTY_TEMPLATE = os.path.join(os.path.dirname(__file__), '院系升旗装备分配表模板.xlsx')

def generate_faculty_excel(persons, changed):
    wb = openpyxl.load_workbook(FACULTY_TEMPLATE)
    yellow_fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
    sorted_persons = sort_people_by_uniform(persons)
    ws1 = wb['装备分配']
    for row in range(2, ws1.max_row + 1):
        for col in range(1, 7): ws1.cell(row=row, column=col).value = None
    for i, p in enumerate(sorted_persons):
        row = i + 2
        name_changed = changed.get(p['name'], {})
        ws1.cell(row=row, column=1).value = p['name']
        ws1.cell(row=row, column=2).value = p.get('uniform', '')
        ws1.cell(row=row, column=3).value = p.get('hat', '')
        ws1.cell(row=row, column=4).value = p.get('boots', '')
        ws1.cell(row=row, column=5).value = p.get('belt', '')
        if name_changed:
            notes = []
            type_names = {'uniform': '礼服', 'hat': '礼帽', 'boots': '马靴', 'belt': '腰带'}
            for t, new in name_changed.items():
                notes.append(f'{type_names.get(t, t)}→{new}')
            ws1.cell(row=row, column=6).value = '；'.join(notes)
            change_map = {'uniform': 2, 'hat': 3, 'boots': 4, 'belt': 5}
            for eq_type, col in change_map.items():
                if eq_type in name_changed:
                    ws1.cell(row=row, column=col).fill = yellow_fill
    for row in range(len(sorted_persons) + 2, ws1.max_row + 1):
        for col in range(1, 7): ws1.cell(row=row, column=col).value = None
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ── OCR ──
def ocr_faculty_roster(img_bytes, excel_bytes):
    from PIL import Image
    import numpy as np

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as t:
        t.write(img_bytes); ip = t.name
    try:
        img = Image.open(ip).convert('RGB')
        w, h = img.size

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as et:
            et.write(excel_bytes); etmp = et.name
        try:
            wb_tmp = openpyxl.load_workbook(etmp)
            known_names = []
            for row in range(2, wb_tmp['装备分配'].max_row + 1):
                n = wb_tmp['装备分配'].cell(row=row, column=2).value
                if n and str(n).strip(): known_names.append(str(n).strip())
            wb_tmp.close()
        finally:
            os.unlink(etmp)

        TARGET_W = min(w, 2000)
        scale = TARGET_W / w
        new_w, new_h = TARGET_W, int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        pre = ip + '_pre.png'; img.save(pre)

        reader = get_ocr_reader()
        results = reader.readtext(np.array(img), detail=1, low_text=0.2, text_threshold=0.4)

        filtered = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            t = text.strip()
            if not t: continue
            if x1 <= 5 and y1 <= 5: continue
            if x3 >= new_w - 5 and y3 >= new_h - 5: continue
            filtered.append((bbox, t, conf))
        results = filtered

        blocks = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            blocks.append({
                'text': text, 'x1': x1, 'x3': x3, 'cx': (x1 + x3) / 2,
                'y1': y1, 'y3': y3, 'cy': (y1 + y3) / 2, 'conf': conf
            })

        COL_W = new_w / 8
        blocks.sort(key=lambda b: b['cx'])
        col_buckets = {}
        for b in blocks:
            col_idx = int(b['cx'] // COL_W)
            col_buckets.setdefault(col_idx, []).append(b)
        sorted_cols = sorted(col_buckets.items())

        merged_cols = []
        for col_idx, col_blocks in sorted_cols:
            if merged_cols and col_idx - merged_cols[-1][0] <= 1:
                prev_blocks = merged_cols[-1][1]
                prev_max_x = max(b['x3'] for b in prev_blocks)
                cur_min_x = min(b['x1'] for b in col_blocks)
                if cur_min_x - prev_max_x < COL_W * 0.3:
                    merged_cols[-1] = (merged_cols[-1][0], prev_blocks + col_blocks)
                    continue
            merged_cols.append((col_idx, col_blocks))

        ROLE_KW = ['总负责', '场控', '后勤', '摄影']
        QUEUE_TITLE_KW = ['擎护旗', '队列']
        first_role_col_idx = None
        for i, (_, col_blocks) in enumerate(merged_cols):
            col_text = ' '.join(b['text'] for b in col_blocks)
            if any(kw in col_text for kw in ROLE_KW):
                first_role_col_idx = i; break

        if first_role_col_idx is not None:
            for i in range(len(merged_cols)):
                merged_cols[i] = merged_cols[i] + ({'type': 'role' if i >= first_role_col_idx else 'queue'},)
        else:
            for i in range(len(merged_cols)):
                merged_cols[i] = merged_cols[i] + ({'type': 'queue' if i < 4 else 'role'},)

        def fuzzy_match_name(name, name_list):
            if not name or len(name) < 1: return name
            if name in name_list: return name
            nc = set(name); best, best_score = name, 0
            for ref in name_list:
                rc = set(ref); common = len(nc & rc)
                overlap = common / max(len(nc), len(rc))
                seq = SequenceMatcher(None, name, ref).ratio()
                score = overlap * 10 + seq * 5
                if score > best_score: best_score, best = score, ref
            return best if best_score >= 5 and best != name else name

        queue_names = []
        for col_idx, col_blocks, meta in merged_cols:
            ctype = meta['type']
            col_blocks.sort(key=lambda b: b['y1'])
            merged_texts = []; i = 0
            while i < len(col_blocks):
                b = col_blocks[i]; t = b['text'].strip()
                if len(t) == 1 and i + 1 < len(col_blocks):
                    nb = col_blocks[i + 1]
                    char_h = b['y3'] - b['y1']
                    if char_h > 0 and nb['y1'] - b['y3'] < char_h * 3.0:
                        t = t + nb['text'].strip(); i += 1
                merged_texts.append({'text': t, 'y1': b['y1']}); i += 1
            col_names = []
            for mt in merged_texts:
                t = mt['text'].strip()
                if not t: continue
                if t in QUEUE_TITLE_KW: continue
                if t in ROLE_KW: continue
                for kw in QUEUE_TITLE_KW + ROLE_KW:
                    if kw in t and t != kw: t = t.replace(kw, '').strip()
                if not t: continue
                corrected = fuzzy_match_name(t, known_names)
                col_names.append(corrected)
            if ctype == 'queue':
                for n in col_names:
                    if n and n not in queue_names: queue_names.append(n)

        if known_names:
            all_text = ''.join(b['text'] for b in blocks)
            all_chars = set(all_text)
            for ref_name in known_names:
                if ref_name in queue_names: continue
                rc = set(ref_name)
                hit = all_chars & rc
                if len(hit) >= max(2, len(rc) * 0.5):
                    for b in blocks:
                        if fuzzy_match_name(b['text'], known_names) == ref_name:
                            if ref_name not in queue_names:
                                queue_names.append(ref_name); break
        os.unlink(pre)
        return '\n'.join(queue_names) if queue_names else ''
    finally:
        try: os.unlink(ip)
        except: pass


# ═══════════════════════════════════════
#  页面渲染
# ═══════════════════════════════════════

@st.cache_data(ttl=86400)
def warehouse_data_json():
    """返回物资仓库的裸数据，供 JS 渲染用"""
    import json
    data = {
        "grid": [
            [{"code": "X44-05", "person": "孜英"}, {"code": "X44-04", "person": ""}, {"code": "X43-08", "person": "顾铭文"}, {"code": "X44-06", "person": "林育臣"}, {"code": "X39-02", "person": ""}, {"code": "N43/41-01", "person": "钱俊宇"}, {"code": "N43/41-02", "person": ""}, {"code": "N43/43-01", "person": "章晏华"}, {"code": "N43/43-02", "person": "张博宣"}, {"code": "N43/43-03", "person": "李承哲"}, {"code": "N43/46", "person": ""}, {"code": "N44/44.5", "person": "沈昊"}, {"code": "X42-22", "person": "肖玉茂"}, {"code": "X42-23", "person": "张子昂"}],
            [{"code": "X43-04", "person": "韩钧宇"}, {"code": "X43-05", "person": ""}, {"code": "X43-06", "person": "朱家兴"}, {"code": "X43-07", "person": "柳洋"}, {"code": "X39-01", "person": "楼震霆"}, {"code": "N42/42.5-02", "person": "韦景浩"}, {"code": "N42/42.5-03", "person": "冯敬栩"}, {"code": "N42/42.5-04", "person": "潘睿"}, {"code": "N42/43.5-02", "person": ""}, {"code": "N42/44", "person": ""}, {"code": "N42/44.5", "person": "叶非"}, {"code": "N45/45", "person": "戴傲"}, {"code": "X42-19", "person": "（鞋面损坏）"}, {"code": "X42-21", "person": ""}],
            [{"label": "置物架"}, None, None, {"code": "X43-03", "person": ""}, {"code": "X38-04", "person": "郭婷心"}, {"code": "N42/40.5-02", "person": ""}, {"code": "N42/40.5-03", "person": "王梓丞"}, {"code": "N42/40.5-04", "person": "陆荪桐"}, {"code": "N42/43-01", "person": ""}, {"code": "N42/43-02", "person": ""}, {"code": "N42/43.5-01", "person": ""}, {"label": "置物架"}, None, None],
            [None, None, None, {"code": "X43-02", "person": ""}, {"code": "X38-03", "person": "卢格妤"}, {"code": "N41/42-02", "person": "姚忻成"}, {"code": "N41/42-03", "person": "胡思源"}, {"code": "N41/42-04", "person": "徐顺烨"}, {"code": "N42/42-01", "person": "张煜琦"}, {"code": "N42/42-02", "person": "夏瑞泽"}, {"code": "N42/42.5-01", "person": "张子恒"}, None, None, None],
            [None, None, None, {"code": "X43-01", "person": ""}, {"code": "X38-02", "person": ""}, {"code": "N39/40.5", "person": "韩雅丽"}, {"code": "N40/39.5-01", "person": "孙鸣"}, {"code": "N40/39.5-02", "person": "余佳卉"}, {"code": "N41/42-05", "person": "叶宇轩"}, {"code": "N41/43.5", "person": ""}, {"code": "N42/40.5-01", "person": ""}, None, None, None],
            [None, None, None, {"code": "X42-24", "person": ""}, {"code": "J38-01", "person": ""}, {"code": "N38/40-01", "person": "许诺"}, {"code": "N38/40-02", "person": ""}, {"code": "N38/40-03", "person": "段茗萱"}, {"code": "N40/41", "person": "吕凯进"}, {"code": "N40/41.5", "person": "程锦添"}, {"code": "N41/42-01", "person": "（舟山）"}, None, None, None],
            [None, None, None, None, None, None, None, None, {"code": "N38/41", "person": "江文欣"}, {"code": "N39/38-01", "person": "吴桐"}, {"code": "N39/38-02", "person": "柯天翊"}, {"code": "X42-12", "person": ""}, {"code": "X42-13", "person": ""}, {"code": "X42-17", "person": ""}],
            [{"label": "置物架"}, None, None, None, {"code": "X37-05", "person": "王雨梦"}, {"code": "N37/40", "person": "俞恩祺"}, {"code": "N37/41", "person": "艾克达"}, {"code": "N38/37", "person": "王艺霏"}, {"code": "N38/37.5-01", "person": "张艺"}, {"code": "N38/37.5-02", "person": "章芮容"}, {"code": "N38/37.5-03", "person": "施东隅"}, {"code": "X42-06", "person": "李思齐"}, {"code": "X42-07", "person": "姚爽"}, {"code": "X42-09", "person": ""}],
            [None, None, None, {"code": "J41-03", "person": ""}, {"code": "X37-04", "person": "呼岳洋"}, {"code": "N37/37-04", "person": ""}, {"code": "N37/37.5-01", "person": "林珩"}, {"code": "N37/37.5-02", "person": ""}, {"code": "N37/38-01", "person": "陈涵予"}, {"code": "N37/38-02", "person": "祁子谦"}, {"code": "N37/39.5", "person": "杨阿丽雅"}, {"code": "X42-01", "person": "李秉均"}, {"code": "X42-03", "person": "张嘉靖"}, {"code": "X42-05", "person": "努尔加娜特"}],
            [None, None, {"code": "X45-01", "person": ""}, {"code": "J41-01", "person": "叶栩浩"}, {"code": "X36-01", "person": "纪博雅"}, {"code": "N36/38-02", "person": "马欣雅"}, {"code": "N36/39", "person": "李泽一"}, {"code": "N37/36.5", "person": ""}, {"code": "N37/37-01", "person": ""}, {"code": "N37/37-02", "person": "李诗诗"}, {"code": "N37/37-03", "person": ""}, {"code": "X41-01", "person": "项烨"}, {"code": "X41-02", "person": "吴昕桐"}, {"code": "X41-03", "person": "陈思骆"}],
            [None, None, {"code": "X39-03", "person": "张鹏"}, {"code": "X39-04", "person": ""}, {"code": "J36-02", "person": ""}, {"code": "N35/36-01", "person": "方嫄 董欢瑶"}, {"code": "N35/37", "person": "初姝彤"}, {"code": "N36/36-01", "person": "岳佳凝"}, {"code": "N36/36-02", "person": "方佳瑶"}, {"code": "N36/37", "person": "杨羽茜"}, {"code": "N36/38-01", "person": "邬家琪"}, {"code": "X39-06", "person": ""}, {"code": "X39-07", "person": "文科"}, {"code": "X39-09", "person": ""}]
        ],
        "belts": [
            {"code": "F01", "uniform_size": "F165/80-01", "person": "李泽一", "cabinet": "一柜"},
            {"code": "F02", "uniform_size": "F165/80-02", "person": "", "cabinet": "一柜"},
            {"code": "F03", "uniform_size": "F165/84-01", "person": "林珩", "cabinet": "一柜"},
            {"code": "F04", "uniform_size": "F165/84-02", "person": "方佳瑶", "cabinet": "一柜"},
            {"code": "F05", "uniform_size": "F165/84-03", "person": "纪博雅", "cabinet": "一柜"},
            {"code": "F06", "uniform_size": "F170/84-06", "person": "韩雅丽", "cabinet": "四柜"},
            {"code": "F07", "uniform_size": "F165/88-01", "person": "李诗诗、王雨梦", "cabinet": "二柜"},
            {"code": "F08", "uniform_size": "F165/88-02", "person": "郭婷心", "cabinet": "二柜"},
            {"code": "F09", "uniform_size": "F165/88-03", "person": "岳佳凝、吴桐", "cabinet": "二柜"},
            {"code": "F10", "uniform_size": "F165/88-04", "person": "江文欣、董欢瑶", "cabinet": "二柜"},
            {"code": "F11", "uniform_size": "F170/84-01", "person": "方嫄", "cabinet": "四柜"},
            {"code": "F12", "uniform_size": "F170/84-02", "person": "柯天翊", "cabinet": "四柜"},
            {"code": "F13", "uniform_size": "F170/84-03", "person": "祁子谦、段茗萱", "cabinet": "四柜"},
            {"code": "F14", "uniform_size": "F170/84-04", "person": "张艺", "cabinet": "四柜"},
            {"code": "F15", "uniform_size": "F170/88-01", "person": "施东隅", "cabinet": "四柜"},
            {"code": "F16", "uniform_size": "F170/88-02", "person": "呼岳洋、章芮容", "cabinet": "四柜"},
            {"code": "F17", "uniform_size": "F170/92-01", "person": "艾克达、卢格妤", "cabinet": "五柜"},
            {"code": "F18", "uniform_size": "F170/92-02", "person": "许诺、余佳卉", "cabinet": "五柜"},
            {"code": "F19", "uniform_size": "F175/88-01", "person": "马欣雅", "cabinet": "二柜"},
            {"code": "F20", "uniform_size": "F175/92-01", "person": "俞恩祺、陈涵予", "cabinet": "三柜"},
            {"code": "M01", "uniform_size": "M175/88-01", "person": "陈思骆", "cabinet": "一柜"},
            {"code": "M02", "uniform_size": "M175/88-02", "person": "吴昕桐", "cabinet": "一柜"},
            {"code": "M03", "uniform_size": "M175/92-01", "person": "楼震霆、潘睿", "cabinet": "一柜"},
            {"code": "M04", "uniform_size": "M175/96-01", "person": "张鹏", "cabinet": "三柜"},
            {"code": "M05", "uniform_size": "M175/96-02", "person": "叶宇轩", "cabinet": "三柜"},
            {"code": "M06", "uniform_size": "M175/96-03", "person": "文科", "cabinet": "三柜"},
            {"code": "M07", "uniform_size": "M175/96-04", "person": "冯敬栩", "cabinet": "三柜"},
            {"code": "M08", "uniform_size": "M180/92-01", "person": "张嘉靖", "cabinet": "三柜"},
            {"code": "M09", "uniform_size": "M180/92-02", "person": "肖玉茂", "cabinet": "三柜"},
            {"code": "M10", "uniform_size": "M180/92-03", "person": "夏瑞泽", "cabinet": "三柜"},
            {"code": "M11", "uniform_size": "M180/92-04", "person": "胡思源", "cabinet": "三柜"},
            {"code": "M12", "uniform_size": "M180/92-05", "person": "李思齐", "cabinet": "二柜"},
            {"code": "M13", "uniform_size": "M180/92-06", "person": "叶栩浩", "cabinet": "二柜"},
            {"code": "M14", "uniform_size": "M185/100-03", "person": "", "cabinet": "六柜"},
            {"code": "M15", "uniform_size": "M180/96-05", "person": "朱家兴、姚忻成", "cabinet": "五柜"},
            {"code": "M16", "uniform_size": "M180/96-01", "person": "项烨、姚爽", "cabinet": "五柜"},
            {"code": "M17", "uniform_size": "M180/96-02", "person": "柳洋、孙鸣", "cabinet": "五柜"},
            {"code": "M18", "uniform_size": "M180/96-03", "person": "章晏华", "cabinet": "五柜"},
            {"code": "M19", "uniform_size": "M180/96-04", "person": "沈昊、王梓丞", "cabinet": "五柜"},
            {"code": "M20", "uniform_size": "M175/92-02", "person": "吕凯进", "cabinet": "一柜"},
            {"code": "M21", "uniform_size": "M180/96-06", "person": "钱俊宇、努尔加娜特、张子恒", "cabinet": "四柜"},
            {"code": "M22", "uniform_size": "M180/96-07", "person": "张煜琦、孜英", "cabinet": "四柜"},
            {"code": "M23", "uniform_size": "M180/100-01", "person": "张子昂", "cabinet": "五柜"},
            {"code": "M24", "uniform_size": "M185/100-01", "person": "张博宣、戴傲", "cabinet": "六柜"},
            {"code": "M25", "uniform_size": "M185/100-02", "person": "顾铭文、韦景浩、林育臣", "cabinet": "六柜"},
            {"code": "M26", "uniform_size": "M185/96-01", "person": "李承哲", "cabinet": "六柜"},
            {"code": "M27", "uniform_size": "M185/96-02", "person": "韩钧宇、陆荪桐", "cabinet": "六柜"}
        ],
        "uniforms": [
            {"code": "F165/80-01", "belt": "F01", "person": "李泽一", "cabinet": "一柜"},
            {"code": "F165/80-02", "belt": "F02", "person": "", "cabinet": "一柜"},
            {"code": "F165/84-01", "belt": "F03", "person": "林珩", "cabinet": "一柜"},
            {"code": "F165/84-02", "belt": "F04", "person": "方佳瑶", "cabinet": "一柜"},
            {"code": "F165/84-03", "belt": "F05", "person": "纪博雅", "cabinet": "一柜"},
            {"code": "F165/84-04", "belt": "", "person": "", "cabinet": "一柜"},
            {"code": "F165/84-05", "belt": "", "person": "", "cabinet": "一柜"},
            {"code": "F165/88-01", "belt": "F07", "person": "李诗诗、王雨梦", "cabinet": "二柜"},
            {"code": "F165/88-02", "belt": "F08", "person": "郭婷心", "cabinet": "二柜"},
            {"code": "F165/88-03", "belt": "F09", "person": "岳佳凝、吴桐", "cabinet": "二柜"},
            {"code": "F165/88-04", "belt": "F10", "person": "江文欣、董欢瑶", "cabinet": "二柜"},
            {"code": "F170/84-01", "belt": "F11", "person": "方嫄", "cabinet": "四柜"},
            {"code": "F170/84-02", "belt": "F12", "person": "柯天翊", "cabinet": "四柜"},
            {"code": "F170/84-03", "belt": "F13", "person": "祁子谦、段茗萱", "cabinet": "四柜"},
            {"code": "F170/84-04", "belt": "F14", "person": "张艺", "cabinet": "四柜"},
            {"code": "F170/84-05", "belt": "", "person": "", "cabinet": "四柜"},
            {"code": "F170/84-06", "belt": "F06", "person": "韩雅丽", "cabinet": "四柜"},
            {"code": "F170/88-01", "belt": "F15", "person": "施东隅", "cabinet": "四柜"},
            {"code": "F170/88-02", "belt": "F16", "person": "呼岳洋、章芮容", "cabinet": "四柜"},
            {"code": "F170/88-03", "belt": "", "person": "", "cabinet": "四柜"},
            {"code": "F170/92-01", "belt": "F17", "person": "艾克达、卢格妤", "cabinet": "五柜"},
            {"code": "F170/92-02", "belt": "F18", "person": "许诺、余佳卉", "cabinet": "五柜"},
            {"code": "F175/88-01", "belt": "F19", "person": "马欣雅", "cabinet": "二柜"},
            {"code": "F175/88-02", "belt": "", "person": "", "cabinet": "三柜"},
            {"code": "F175/92-01", "belt": "F20", "person": "俞恩祺、陈涵予", "cabinet": "三柜"},
            {"code": "F175/92-02", "belt": "", "person": "", "cabinet": "三柜"},
            {"code": "M175/88-01", "belt": "M01", "person": "陈思骆", "cabinet": "一柜"},
            {"code": "M175/88-02", "belt": "M02", "person": "吴昕桐", "cabinet": "一柜"},
            {"code": "M175/92-01", "belt": "M03", "person": "楼震霆、潘睿", "cabinet": "一柜"},
            {"code": "M175/92-02", "belt": "M20", "person": "吕凯进", "cabinet": "一柜"},
            {"code": "M175/96-01", "belt": "M04", "person": "张鹏", "cabinet": "三柜"},
            {"code": "M175/96-02", "belt": "M05", "person": "叶宇轩", "cabinet": "三柜"},
            {"code": "M175/96-03", "belt": "M06", "person": "文科", "cabinet": "三柜"},
            {"code": "M175/96-04", "belt": "M07", "person": "冯敬栩", "cabinet": "三柜"},
            {"code": "M180/92-05", "belt": "M12", "person": "李思齐", "cabinet": "二柜"},
            {"code": "M180/92-06", "belt": "M13", "person": "叶栩浩", "cabinet": "二柜"},
            {"code": "M180/92-07", "belt": "", "person": "", "cabinet": "二柜"},
            {"code": "M180/92-08", "belt": "", "person": "", "cabinet": "二柜"},
            {"code": "M180/92-10", "belt": "", "person": "", "cabinet": "二柜"},
            {"code": "M180/92-11", "belt": "", "person": "", "cabinet": "二柜"},
            {"code": "M180/92-01", "belt": "M08", "person": "张嘉靖", "cabinet": "三柜"},
            {"code": "M180/92-02", "belt": "M09", "person": "肖玉茂", "cabinet": "三柜"},
            {"code": "M180/92-03", "belt": "M10", "person": "夏瑞泽", "cabinet": "三柜"},
            {"code": "M180/92-04", "belt": "M11", "person": "胡思源", "cabinet": "三柜"},
            {"code": "M180/92-09", "belt": "", "person": "", "cabinet": "五柜"},
            {"code": "M180/92-12", "belt": "", "person": "", "cabinet": "五柜"},
            {"code": "M180/96-06", "belt": "M21", "person": "钱俊宇、努尔加娜特、张子恒", "cabinet": "四柜"},
            {"code": "M180/96-07", "belt": "M22", "person": "张煜琦、孜英", "cabinet": "四柜"},
            {"code": "M180/96-01", "belt": "M16", "person": "项烨、姚爽", "cabinet": "五柜"},
            {"code": "M180/96-02", "belt": "M17", "person": "柳洋、孙鸣", "cabinet": "五柜"},
            {"code": "M180/96-03", "belt": "M18", "person": "章晏华", "cabinet": "五柜"},
            {"code": "M180/96-04", "belt": "M19", "person": "沈昊、王梓丞", "cabinet": "五柜"},
            {"code": "M180/96-05", "belt": "M15", "person": "朱家兴、姚忻成", "cabinet": "五柜"},
            {"code": "M180/96-08", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M180/96-09", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M180/100-01", "belt": "M23", "person": "张子昂", "cabinet": "五柜"},
            {"code": "M180/100-02", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M180/100-03", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M180/100-04", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M180/100-05", "belt": "", "person": "", "cabinet": "六柜"},
            {"code": "M185/96-01", "belt": "M26", "person": "李承哲", "cabinet": "六柜"},
            {"code": "M185/96-02", "belt": "M27", "person": "韩钧宇、陆荪桐", "cabinet": "六柜"},
            {"code": "M185/100-01", "belt": "M24", "person": "张博宣、戴傲", "cabinet": "六柜"},
            {"code": "M185/100-02", "belt": "M25", "person": "顾铭文、韦景浩、林育臣", "cabinet": "六柜"},
            {"code": "M185/100-03", "belt": "M14", "person": "", "cabinet": "六柜"}
        ]
    }
    return json.dumps(data, ensure_ascii=False)


def render_warehouse():
    """直接在 Python 中渲染物资仓库为 HTML，不需要 JS 动态生成"""
    import json
    data = json.loads(warehouse_data_json())
    grid = data['grid']
    belts = data['belts']
    uniforms = data['uniforms']

    SHIRT_SET = {'F165/80-01','F165/80-02','F165/84-02','F165/88-01','F165/88-02','F165/88-03','F165/88-04','M180/92-05','M175/96-02','F170/84-01','F170/84-02','F170/84-03','F170/84-06','F170/88-01','F170/88-02','F170/92-01'}

    h = []

    # ── 马靴区域 ──
    flat = []
    for r in grid:
        for c in r:
            if c and c.get('code'): flat.append(c)

    cg = [(1,4),(2,4),(3,3),(4,3)]
    rg = [('A',2),('B',4),('C',5)]

    h.append('<div class="section"><div class="section-header"><span class="tag" style="background:#E65100">🥾</span>马靴 · {}库位</div>'.format(len(flat)))
    h.append('<div class="table-wrap"><div class="grid-table" style="grid-template-columns:28px repeat(14,minmax(68px,1fr))">')
    h.append('<div class="cell gh" style="background:#fafafa"></div>')
    for gn, gc in cg:
        h.append('<div class="cell gh" style="grid-column:span {};background:var(--green-700);color:var(--gold);font-weight:700;font-family:var(--font-heading)">{}</div>'.format(gc, gn))

    ri = 0
    for rn, rr in rg:
        for lri, row in enumerate(grid[ri:ri+rr]):
            if lri == 0:
                h.append('<div class="cell gh" style="grid-row:span {};writing-mode:vertical-lr;background:var(--green-700);color:var(--gold);font-weight:700;font-family:var(--font-heading)">{}</div>'.format(rr, rn))
            for ci in range(14):
                cell = row[ci] if ci < len(row) else None
                if cell and cell.get('code'):
                    nm = cell.get('person', '')
                    h.append('<div class="cell boot" onclick="showDetail(\'boot\',\'{}\',\'{}\')"><span class="cc">{}</span>'.format(cell['code'], nm, cell['code']))
                    if nm: h.append('<span class="cn">{}</span>'.format(nm))
                    h.append('</div>')
                else:
                    h.append('<div class="cell empty"></div>')
        ri += rr
    h.append('</div></div></div>')

    # ── 腰带区域 ──
    h.append('<div class="section"><div class="section-header"><span class="tag" style="background:#C62828">🎽</span>腰带 · {}项</div><div class="table-wrap">'.format(len(belts)))
    cabs = ['一柜','二柜','三柜','四柜','五柜','六柜']
    ccl = ['#E65100','#FF8F00','#F9A825','#FFB300','#FFC107','#FFCA28']
    for ci, cab in enumerate(cabs):
        grp = [b for b in belts if b['cabinet'] == cab]
        if not grp: continue
        h.append('<div class="cab-label" style="color:{};border-color:{}">{} · {}项</div>'.format(ccl[ci], ccl[ci], cab, len(grp)))
        h.append('<div class="grid-table" style="grid-template-columns:repeat(auto-fill,minmax(80px,1fr))">')
        for item in grp:
            nm = item.get('person', '')
            h.append('<div class="cell belt" onclick="showDetail(\'belt\',\'{}\',\'{}\')"><span class="cc">{}</span>'.format(item['code'], nm, item['code']))
            if nm: h.append('<span class="cn">{}</span>'.format(nm))
            h.append('</div>')
        h.append('</div>')
    h.append('</div></div>')

    # ── 礼服区域 ──
    h.append('<div class="section"><div class="section-header"><span class="tag" style="background:#1565C0">👔</span>礼服 · {}项</div><div class="table-wrap">'.format(len(uniforms)))
    for ci, cab in enumerate(cabs):
        grp = [u for u in uniforms if u['cabinet'] == cab]
        if not grp: continue
        h.append('<div class="cab-label" style="color:{};border-color:{}">{} · {}项</div>'.format(ccl[ci], ccl[ci], cab, len(grp)))
        h.append('<div class="grid-table" style="grid-template-columns:repeat(auto-fill,minmax(80px,1fr))">')
        for item in grp:
            nm = item.get('person', '')
            st = '<span class="ct" style="background:var(--green-500)">衬衫</span>' if item['code'] in SHIRT_SET else ''
            h.append('<div class="cell uniform" onclick="showDetail(\'uniform\',\'{}\',\'{}\')"><span class="cc">{}</span>'.format(item['code'], nm, item['code']))
            if nm: h.append('<span class="cn">{}</span>'.format(nm))
            if st: h.append(st)
            h.append('</div>')
        h.append('</div>')
    h.append('</div></div>')

    return '\n'.join(h)


# ═══════════════════════════════════════
#  主路由
# ═══════════════════════════════════════

if 'page' not in st.session_state:
    st.session_state.page = 'home'

inject_css()

# ── 全局样式 + Header ──
st.markdown("""
<style>
/* 修复 Streamlit 默认 padding 导致的 header 遮挡 */
.stApp {background-color: #F5F1E6}
.block-container {padding: 0 !important; max-width: 100% !important}
section.main > .block-container {padding-top: 0 !important}

/* Header 区域 */
.flag-header {
    background:#B81616; color:#fff; padding:18px 32px;
    display:flex; align-items:center; justify-content:space-between;
    border-bottom:2px solid rgba(245,197,24,.3);
    margin: 0 0 24px 0;
}
.flag-header h1 {
    font-family:'SimSun','KaiTi','宋体',serif;
    font-size:20px; font-weight:700; letter-spacing:.08em; color:#fff; margin:0;
}
.flag-header .star {color:#F5C518; font-size:16px}

/* Footer */
.flag-footer {
    text-align:center; padding:28px; color:#1a3a2a;
    font-family:'SimSun','KaiTi',serif; font-size:12px;
    letter-spacing:.06em; border-top:1px solid rgba(184,22,22,.12);
    margin:40px 0 0 0;
}
.flag-footer .star {color:#F5C518; font-size:10px; margin:0 6px}

/* 首页卡片 */
.home-card {
    background:#fff; border:1px solid rgba(184,22,22,.08); border-left:3px solid #F5C518;
    border-radius:8px; padding:32px 24px; text-align:center;
    box-shadow:0 2px 12px rgba(0,0,0,.04);
    transition:all .3s ease; cursor:pointer; display:block; text-decoration:none; color:inherit;
}
.home-card:hover {border-left-color:#B81616;transform:translateY(-4px);box-shadow:0 8px 28px rgba(184,22,22,.1)}
.home-card .icon {font-size:40px;margin-bottom:10px}
.home-card h3 {
    font-family:'SimSun','KaiTi',serif;font-size:18px;color:#0f2518;
    margin:8px 0 10px;font-weight:700;letter-spacing:.05em;
}
.home-card p {font-size:14px;color:#5c4a3a;line-height:1.7;margin:0}

/* Streamlit 按钮重写 — 国旗红 */
.stButton > button {
    background-color: #B81616 !important;
    color: #fff !important;
    border: none !important;
    font-weight: 700 !important;
    font-family: 'SimSun','KaiTi',serif !important;
    font-size: 14px !important;
    letter-spacing: .05em !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    background-color: #8E1010 !important;
    box-shadow: 0 4px 12px rgba(184,22,22,.25) !important;
}
.stButton > button:disabled {
    background-color: #D9A4A4 !important;
    color: rgba(255,255,255,.7) !important;
}

/* 文件上传区域 */
[data-testid="stFileUploader"] {
    background: #fff;
    border: 2px dashed #d4d4cc;
    border-radius: 8px;
    padding: 20px;
}
[data-testid="stFileUploader"]:hover {border-color:#B81616}

/* text_area */
textarea {font-family:'Microsoft YaHei',sans-serif !important;font-size:14px !important}

/* expander */
[data-testid="stExpander"] {
    background:#fff;border:1px solid rgba(184,22,22,.08);border-radius:8px;
}

/* metric */
[data-testid="stMetricValue"] {font-size:2rem !important;font-weight:700 !important}

/* dataframe 表格 */
[data-testid="stDataFrame"] {font-size:13px}
[data-testid="stDataFrame"] th {
    background:#1a3a2a !important;color:#e0d0a0 !important;
    font-family:'SimSun','KaiTi',serif !important;font-size:12px;
}

/* 仓库网格样式 */
:root {--flag-red:#B81616;--gold:#F5C518;--green-700:#1a3a2a;--green-500:#2d5a3f;
       --cream:#F5F1E6;--white:#fff;--ink:#2c1810;--ink-light:#5c4a3a;--ink-faint:#9c8a7a;
       --font-heading:'SimSun','KaiTi',serif;--font-body:'Microsoft YaHei',sans-serif}
.section {margin-bottom:16px;background:var(--white);border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.04);overflow:hidden;border:1px solid rgba(184,22,22,.06);border-left:3px solid var(--gold)}
.section-header {padding:10px 16px;font-size:13px;font-weight:700;border-bottom:2px solid rgba(184,22,22,.08);display:flex;align-items:center;gap:10px;background:var(--white);font-family:var(--font-heading);letter-spacing:.04em;color:#0f2518}
.section-header .tag {padding:4px 12px;border-radius:4px;color:var(--white);font-size:11px;font-weight:700}
.table-wrap {overflow-x:auto;-webkit-overflow-scrolling:touch;padding:6px}
.grid-table {display:grid;gap:2px;padding:4px}
.cell {border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:10px 8px;min-width:72px;min-height:52px;cursor:pointer;transition:all .15s;text-align:center;border:1px solid transparent}
.cell:hover {transform:translateY(-2px);box-shadow:0 3px 12px rgba(0,0,0,.1)}
.cell .cc {font-weight:700;font-size:11px;margin-bottom:2px}
.cell .cn {font-size:10px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-light)}
.cell .ct {font-size:9px;color:var(--white);padding:1px 5px;border-radius:3px;margin-top:2px}
.cell.gh {min-width:auto;min-height:24px;padding:2px 4px;font-size:11px}
.cell.gh:hover {transform:none;box-shadow:none}
.cell.empty {background:#fafaf7;border-color:#e8e0d8;cursor:default}
.cell.empty:hover {transform:none;box-shadow:none}
.cell.boot {background:#FFF3E0;border-color:#FFE0B2}.cell.boot .cc {color:#BF360C}
.cell.belt {background:#FCE4EC;border-color:#F8BBD0}.cell.belt .cc {color:#880E4F}
.cell.uniform {background:#E3F2FD;border-color:#BBDEFB}.cell.uniform .cc {color:#0D47A1}
.cab-label {font-size:11px;font-weight:700;padding:4px 12px;border-left:3px solid;margin:6px 0 2px;font-family:var(--font-heading);letter-spacing:.04em}
</style>

<div class="flag-header">
  <div style="display:flex;align-items:center;gap:12px">
    <span class="star">&#9733;</span>
    <h1>浙江大学国旗仪仗队</h1>
  </div>
  <span class="star">&#9733;</span>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════
# 页面渲染
# ════════════════════════════════

if st.session_state.page == 'home':
    st.markdown("""
    <style>
    .entries-wrap {max-width:780px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:24px}
    @media(max-width:640px){.entries-wrap{grid-template-columns:1fr}}
    </style>
    <div class="entries-wrap">
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="home-card">
          <div class="icon">&#127891;</div>
          <h3>院系升旗礼服分配</h3>
          <p>上传库存表 + 拍照上传人员安排表<br>自动识别 → 按尺寸排序 → 冲突检测 → 下载分配表</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入", key="btn_faculty", use_container_width=True):
            st.session_state.page = 'faculty'; st.rerun()

    with col2:
        st.markdown("""
        <div class="home-card">
          <div class="icon">&#128230;</div>
          <h3>物资仓库</h3>
          <p>马靴 · 腰带 · 礼服 存放位置<br>搜索库位 / 姓名 / 尺码</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入", key="btn_warehouse", use_container_width=True):
            st.session_state.page = 'warehouse'; st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="flag-footer">
      <span class="star">&#9733;</span> 浙江大学国旗仪仗队 &copy; 2026 <span class="star">&#9733;</span>
    </div>
    """, unsafe_allow_html=True)


elif st.session_state.page == 'faculty':
    # 返回按钮
    if st.button("← 返回首页", key="back_home"):
        st.session_state.page = 'home'; st.rerun()

    st.markdown("---")

    # 步骤卡片
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
      <span style="width:28px;height:28px;background:#B81616;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-family:'SimSun',serif;font-size:14px;flex-shrink:0">1</span>
      <span style="font-family:'SimSun',serif;font-weight:700;font-size:16px;color:#0f2518">上传礼服库存表</span>
    </div>
    """, unsafe_allow_html=True)
    excel_file = st.file_uploader("拖拽或点击上传 .xlsx 文件", type=['xlsx'], key="fac_excel", label_visibility="collapsed")

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:24px 0 16px 0">
      <span style="width:28px;height:28px;background:#B81616;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-family:'SimSun',serif;font-size:14px;flex-shrink:0">2</span>
      <span style="font-family:'SimSun',serif;font-weight:700;font-size:16px;color:#0f2518">拍照上传人员安排表</span>
      <span style="font-size:12px;color:#9c8a7a">（可选，AI 自动识别）</span>
    </div>
    """, unsafe_allow_html=True)
    image_file = st.file_uploader("上传照片", type=['png','jpg','jpeg'], key="fac_img", label_visibility="collapsed")

    st.markdown("""
    <div style="color:#9c8a7a;font-size:12px;text-align:center;margin:8px 0 16px 0">—— 或手动输入 ——</div>
    """, unsafe_allow_html=True)

    ocr_default = st.session_state.get('ocr_roster', '')
    roster = st.text_area("队列人员（每行一人或顿号分隔）", value=ocr_default,
                          placeholder="林珩\n韩雅丽\n艾克达\n张鹏\n夏瑞泽\n戴傲\n叶宇轩",
                          key="fac_roster", height=130, label_visibility="collapsed")

    with st.expander("其他角色（可选，不参与分配）"):
        c1, c2 = st.columns(2)
        m1 = c1.text_input("总负责", key="fm1")
        m2 = c2.text_input("场控", key="fm2")
        m3, m4 = st.columns(2)
        m3_ = m3.text_input("后勤", key="fm3")
        m4_ = m4.text_input("摄影", key="fm4")

    can_gen = excel_file and (roster.strip() or image_file)
    if st.button("\U0001F50D 预览排序 & 生成分配表", disabled=not can_gen, use_container_width=True):
        if excel_file:
            with st.spinner("正在处理..."):
                try:
                    excel_bytes = excel_file.getvalue()

                    if image_file:
                        img_bytes = image_file.getvalue()
                        if len(img_bytes) > 0:
                            ocr_text = ocr_faculty_roster(img_bytes, excel_bytes)
                            if ocr_text:
                                st.session_state.ocr_roster = ocr_text
                                st.info("已识别人员名单，请核对后再次点击生成按钮")
                                st.stop()  # 不用 rerun——让用户手动确认后再点

                    if not roster.strip():
                        st.error("请提供队列人员名单"); st.stop()

                    queue_names = []
                    for chunk in re.split(r'[、，,\n\s]+', roster.strip()):
                        n = chunk.strip()
                        if len(n) >= 2: queue_names.append(n)

                    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as t:
                        t.write(excel_bytes); tmp = t.name

                    try:
                        wb = openpyxl.load_workbook(tmp)
                        all_persons = parse_equipment_sheet(wb['装备分配'])
                        name_map = {p['name']: p for p in all_persons}
                        pool = build_pool(wb)

                        faculty_persons = [dict(name_map[n]) for n in queue_names if n in name_map]
                        missing = [n for n in queue_names if n not in name_map]

                        conflicts = detect_faculty_conflicts(faculty_persons)
                        reassigns, changed = resolve_faculty_conflicts(conflicts, faculty_persons, pool)
                        b64 = generate_faculty_excel(faculty_persons, changed)
                        sorted_people = sort_people_by_uniform(faculty_persons)

                        st.success(f"生成完成: {len(faculty_persons)} 人, {len(conflicts)} 冲突, {len(reassigns)} 重分配")

                        c1, c2, c3 = st.columns(3)
                        c1.metric("冲突数", len(conflicts))
                        c2.metric("重分配", len(reassigns))
                        c3.metric("受影响人数", len(set(r['person'] for r in reassigns)))

                        # 排序列表
                        st.markdown("#### 排序后人员列表")
                        import pandas as pd
                        rows = []
                        for i, p in enumerate(sorted_people):
                            ch = changed.get(p['name'], {})
                            rows.append({
                                "序号": i+1, "姓名": p['name'],
                                "性别": '女' if p['gender']=='F' else '男',
                                "礼服": p.get('uniform',''),
                                "礼帽": p.get('hat',''),
                                "马靴": p.get('boots',''),
                                "腰带": p.get('belt',''),
                                "变更": '; '.join(f'{t}→{nv}' for t,nv in ch.items()) if ch else ''
                            })
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                        if conflicts:
                            st.markdown("#### 冲突详情")
                            type_names = {'uniform':'礼服','hat':'礼帽','boots':'马靴','belt':'腰带'}
                            st.dataframe(pd.DataFrame([
                                {"装备": type_names.get(c['item_type'],c['item_type']),
                                 "编号": c['item_code'], "需变动": c['person_to_move'],
                                 "保留": c['person_to_keep']} for c in conflicts
                            ]), use_container_width=True, hide_index=True)

                        if reassigns:
                            st.markdown("#### 重分配方案")
                            st.dataframe(pd.DataFrame([
                                {"姓名": r['person'],
                                 "装备": type_names.get(r['item_type'],r['item_type']),
                                 "旧编号": r['old_item'], "新编号": r['new_item']} for r in reassigns
                            ]), use_container_width=True, hide_index=True)

                        st.download_button("📥 下载礼服分配表 (.xlsx)",
                                          data=base64.b64decode(b64),
                                          file_name="院系升旗礼服分配.xlsx",
                                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                          use_container_width=True)

                    finally:
                        os.unlink(tmp)

                except Exception as e:
                    import traceback
                    st.error(f"生成失败: {e}")
                    with st.expander("详细错误"): st.code(traceback.format_exc())


elif st.session_state.page == 'warehouse':
    if st.button("← 返回首页", key="wh_back"):
        st.session_state.page = 'home'; st.rerun()

    st.markdown("---")

    # 搜索栏
    st.text_input("搜索库位 / 姓名 / 尺码...", key="wh_search",
                   placeholder="搜索库位 / 姓名 / 尺码...", label_visibility="collapsed")

    # 渲染仓库
    wh_html = render_warehouse()
    st.markdown(wh_html, unsafe_allow_html=True)
