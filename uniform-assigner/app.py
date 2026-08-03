"""礼服分配系统 - Streamlit 版，部署到 Streamlit Cloud 后公网可访问"""
import streamlit as st
import base64, io, os, re, tempfile
from difflib import SequenceMatcher

st.set_page_config(page_title="礼服自动分配系统", page_icon="🎖️", layout="wide", initial_sidebar_state="collapsed")

YELLOW = 'FFFFFF00'

# ═══════════════════════════════════════════════════════════════
# 初始化 session state
# ═══════════════════════════════════════════════════════════════
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# ═══════════════════════════════════════════════════════════════
# EasyOCR 缓存（全局单例，防止每次都重新加载模型）
# ═══════════════════════════════════════════════════════════════
@st.cache_resource
def get_ocr_reader():
    import easyocr
    return easyocr.Reader(['ch_sim'], gpu=False)


# ═══════════════════════════════════════════════════════════════
# 业务逻辑（全部从 server.py 复制，不改）
# ═══════════════════════════════════════════════════════════════

def fuzzy_match(ocr_name, known_names):
    """将 OCR 误识别的名字匹配到最接近的已知人名"""
    if not known_names:
        return ocr_name
    if ocr_name in known_names:
        return ocr_name
    cleaned = re.sub(r'[_|^~\s\d]+', '', ocr_name)
    if cleaned in known_names:
        return cleaned
    for ref in known_names:
        if len(ref) >= 2 and len(cleaned) >= 2 and cleaned[:2] == ref[:2]:
            return ref
    best, best_score = None, 0
    for ref in known_names:
        common = len(set(cleaned) & set(ref))
        ratio = SequenceMatcher(None, cleaned, ref).ratio()
        score = common * 3 + ratio * 5
        if score > best_score:
            best_score, best = score, ref
    if best and best_score >= 6:
        return best
    return re.sub(r'[_|^~\s\d]+', '', ocr_name)


def parse_equipment_sheet(ws):
    persons = []
    for row in range(2, ws.max_row+1):
        name = ws.cell(row=row, column=2).value
        if not name: continue
        name = str(name).strip()
        uni  = str(ws.cell(row=row, column=3).value or '').strip()
        hat  = str(ws.cell(row=row, column=4).value or '').strip()
        boots= str(ws.cell(row=row, column=5).value or '').strip()
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
    return [dict(item_code=k.split('|')[1], item_type=k.split('|')[0], shared_by=list(v)) for k,v in m.items()]


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
            if item.startswith(gender):
                candidates.append((0, item))
    if not candidates:
        for item in available:
            candidates.append((999998, item))
    if not candidates:
        candidates = [(999999, x) for x in all_items if x.startswith(gender)]
    candidates.sort()
    return candidates[0][1] if candidates else None


def build_pool(wb):
    pool = dict(uniform=set(), hat=set())
    for row in range(2, wb['装备分配'].max_row+1):
        for col,key in [(3,'uniform'),(4,'hat')]:
            v = str(wb['装备分配'].cell(row=row, column=col).value or '').strip()
            if v: pool[key].add(v)
    for sn in ['礼服腰带摆放','礼帽摆放']:
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
            alt = find_alternative(person, t, used[t], pool[t])
            if alt:
                used[t].discard(person[t]); used[t].add(alt)
                reassigns.append(dict(person=person['name'], item_type=t, old_item=person[t], new_item=alt))
                changed.setdefault(person['name'], {})[t] = alt
                person[t] = alt
    return reassigns, changed


def generate_excel(template_path, persons, changed):
    import openpyxl
    from openpyxl.styles import PatternFill
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
        for col,key in [(3,'uniform'),(4,'hat'),(5,'boots'),(6,'belt'),(7,'note')]:
            cell = ws.cell(row=row, column=col)
            cell.value = p.get(key, '') or None
            if key in ch:
                cell.fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
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


# ── 院系升旗礼服分配 ──

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
                    conflicts.append(dict(
                        item_type=eq_type, item_code=code,
                        person_to_move=names[i], person_to_keep=names[0]
                    ))
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
            reassigns.append(dict(person=person['name'], item_type=t,
                                  old_item=person[t], new_item=alt))
            changed.setdefault(person['name'], {})[t] = alt
            person[t] = alt
    return reassigns, changed


# 模板文件相对于本脚本的位置
FACULTY_TEMPLATE = os.path.join(os.path.dirname(__file__), '院系升旗装备分配表模板.xlsx')


def generate_faculty_excel(persons, changed):
    import openpyxl
    from openpyxl.styles import PatternFill

    wb = openpyxl.load_workbook(FACULTY_TEMPLATE)
    yellow_fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
    sorted_persons = sort_people_by_uniform(persons)
    ws1 = wb['装备分配']

    for row in range(2, ws1.max_row + 1):
        for col in range(1, 7):
            ws1.cell(row=row, column=col).value = None

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
        for col in range(1, 7):
            ws1.cell(row=row, column=col).value = None

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ═══════════════════════════════════════════════════════════════
# OCR 处理（从图片提取文字）
# ═══════════════════════════════════════════════════════════════

def ocr_daily_schedule(img_bytes, excel_bytes):
    """日常模式 OCR：识别排班表照片中的日期+人名"""
    from PIL import Image
    import numpy as np

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as t:
        t.write(img_bytes); ip = t.name

    try:
        img = Image.open(ip).convert('RGB')
        w, h = img.size
        # 从 Excel 加载已知人名
        import openpyxl
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

        scale = max(1, 800 // w)
        img = img.resize((w * scale, h * scale), Image.LANCZOS)
        pre = ip + '_pre.png'; img.save(pre)

        reader = get_ocr_reader()
        results = reader.readtext(np.array(img), detail=1)

        days_info = []
        name_entries = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            cx = (x1 + x3) / 2
            t = text.strip()
            if any(d in t for d in ['周一','周二','周三','周四','周五']):
                days_info.append({'day': t, 'x1': x1, 'x2': x3, 'cx': cx})
            elif len(t) >= 2:
                name_entries.append({'name': t, 'x': cx, 'y': (y1+y3)/2, 'conf': conf})

        days_info.sort(key=lambda d: d['x1'])

        grouped = {d['day']: [] for d in days_info}
        if days_info:
            col_width = (days_info[-1]['x2'] - days_info[0]['x1']) / len(days_info)
            for n in name_entries:
                best_d, best_dist = None, 99999
                for d in days_info:
                    dist = abs(n['x'] - d['cx'])
                    if dist < best_dist: best_dist, best_d = dist, d
                if best_d and best_dist < col_width * 1.3:
                    grouped[best_d['day']].append((n['y'], n['name']))

        ocr_schedule = []
        for day_label, nl in grouped.items():
            seen = set()
            unique = []
            for _, raw_name in sorted(nl):
                corrected = fuzzy_match(raw_name, known_names)
                if corrected not in seen and corrected in known_names:
                    seen.add(corrected); unique.append(corrected)
            if unique: ocr_schedule.append(dict(day=day_label, people=unique))

        os.unlink(pre)

        if ocr_schedule:
            return '\n'.join(d['day'] + '：' + '、'.join(d['people']) for d in ocr_schedule)
        return ''

    finally:
        try: os.unlink(ip)
        except: pass


def ocr_faculty_roster(img_bytes, excel_bytes):
    """院系模式 OCR：5步列聚类方案
    返回 (roster_text, debug_all_text, debug_columns)"""
    from PIL import Image
    import numpy as np
    import math

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as t:
        t.write(img_bytes); ip = t.name

    try:
        img = Image.open(ip).convert('RGB')
        w, h = img.size

        import openpyxl
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

        # ═══ 第一步：只降不升（避免小图放大失真），宁多勿漏 ═══
        TARGET_W = min(w, 2000)
        scale = TARGET_W / w
        new_w, new_h = TARGET_W, int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        pre = ip + '_pre.png'; img.save(pre)

        import easyocr
        reader = easyocr.Reader(['ch_sim'], gpu=False)
        results = reader.readtext(np.array(img), detail=1, low_text=0.2, text_threshold=0.4)

        print(f'[Faculty-OCR] Image: {w}x{h} -> {new_w}x{new_h}, {len(results)} text regions')

        # 过滤真正贴边的噪点（绝对5px，不用百分比，避免误删小图片中的文字）
        filtered = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            t = text.strip()
            if not t: continue
            if x1 <= 5 and y1 <= 5: continue
            if x3 >= new_w - 5 and y3 >= new_h - 5: continue
            filtered.append((bbox, t, conf))
        results = filtered

        # 构建 debug_all_text（全部原始文本+坐标）
        debug_raw_lines = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            debug_raw_lines.append(
                f'{text} | x={x1:.0f}-{x3:.0f} cx={(x1+x3)/2:.0f} y={y1:.0f}-{y3:.0f} cy={(y1+y3)/2:.0f} conf={conf:.2f}'
            )
        debug_all_text = '\n'.join(debug_raw_lines)

        # 把每个文本块整理成统一结构
        blocks = []
        for bbox, text, conf in results:
            x1, y1 = bbox[0]; x3, y3 = bbox[2]
            blocks.append({
                'text': text, 'x1': x1, 'x3': x3, 'cx': (x1 + x3) / 2,
                'y1': y1, 'y3': y3, 'cy': (y1 + y3) / 2, 'conf': conf
            })

        # ═══ 第二步：按 x 坐标列聚类 —— 固定列宽 = 图片宽度 / 8 ═══
        COL_W = new_w / 8
        blocks.sort(key=lambda b: b['cx'])

        # 把所有 block 分配到列
        col_buckets = {}
        for b in blocks:
            col_idx = int(b['cx'] // COL_W)
            if col_idx not in col_buckets:
                col_buckets[col_idx] = []
            col_buckets[col_idx].append(b)

        # 按列号排序
        sorted_cols = sorted(col_buckets.items())  # [(col_idx, [blocks]), ...]

        # 把稀疏的相邻列合并（如果两列间距 < COL_W * 0.5）
        merged_cols = []
        for col_idx, col_blocks in sorted_cols:
            if merged_cols and col_idx - merged_cols[-1][0] <= 1:
                # 相邻列，检查实际 x 范围是否有重叠或接近
                prev_blocks = merged_cols[-1][1]
                prev_max_x = max(b['x3'] for b in prev_blocks)
                cur_min_x = min(b['x1'] for b in col_blocks)
                if cur_min_x - prev_max_x < COL_W * 0.3:
                    merged_cols[-1] = (merged_cols[-1][0], prev_blocks + col_blocks)
                    continue
            merged_cols.append((col_idx, col_blocks))

        # ═══ 第三步：标记角色列，左边所有列全算队列 ═══
        ROLE_KW = ['总负责', '场控', '后勤', '摄影']
        QUEUE_TITLE_KW = ['擎护旗', '队列']

        # 找第一个角色列的索引
        first_role_col_idx = None
        for i, (_, col_blocks) in enumerate(merged_cols):
            col_text = ' '.join(b['text'] for b in col_blocks)
            if any(kw in col_text for kw in ROLE_KW):
                first_role_col_idx = i
                break

        # 标记每列
        if first_role_col_idx is not None:
            # 角色列及右边的列全部标记为 role，左边的全为 queue
            for i in range(len(merged_cols)):
                merged_cols[i] = merged_cols[i] + ({'type': 'role' if i >= first_role_col_idx else 'queue'},)
        else:
            # 强制兜底：没识别到角色关键词，前 4 列全算队列
            for i in range(len(merged_cols)):
                merged_cols[i] = merged_cols[i] + ({'type': 'queue' if i < 4 else 'role'},)

        # ═══ 第四步：人名清洗与兜底匹配 ═══
        def fuzzy_match_name(name, name_list):
            """字符重合度 >= 50% 就尝试还原"""
            if not name or len(name) < 1: return name
            if name in name_list: return name
            nc = set(name)
            best, best_score = name, 0
            for ref in name_list:
                rc = set(ref)
                common = len(nc & rc)
                overlap = common / max(len(nc), len(rc))
                seq = SequenceMatcher(None, name, ref).ratio()
                score = overlap * 10 + seq * 5
                if score > best_score:
                    best_score = score
                    best = ref
            # 重合度 >= 50% 就匹配
            if best_score >= 5 and best != name:
                return best
            return name

        queue_names = []
        debug_col_lines = []

        for col_idx, col_blocks, meta in merged_cols:
            ctype = meta['type']
            cx1 = min(b['x1'] for b in col_blocks)
            cx2 = max(b['x3'] for b in col_blocks)
            col_blocks.sort(key=lambda b: b['y1'])

            # 合并单字：同列上下相邻的单字合并
            merged_texts = []
            i = 0
            while i < len(col_blocks):
                b = col_blocks[i]
                t = b['text'].strip()
                if len(t) == 1 and i + 1 < len(col_blocks):
                    nb = col_blocks[i + 1]
                    char_h = b['y3'] - b['y1']
                    if char_h > 0 and nb['y1'] - b['y3'] < char_h * 3.0:
                        t = t + nb['text'].strip()
                        i += 1
                merged_texts.append({'text': t, 'y1': b['y1']})
                i += 1

            # 提取人名
            col_names = []
            for mt in merged_texts:
                t = mt['text'].strip()
                if not t: continue
                # 剔除纯标题词
                if t in QUEUE_TITLE_KW: continue
                if t in ROLE_KW: continue
                # 剔除混合文本中的标题关键词，保留人名部分
                for kw in QUEUE_TITLE_KW + ROLE_KW:
                    if kw in t and t != kw:
                        t = t.replace(kw, '').strip()
                if not t: continue
                # 模糊匹配
                corrected = fuzzy_match_name(t, known_names)
                col_names.append(corrected)

            debug_col_lines.append(
                f'Col[{col_idx}] type={ctype} x=[{cx1:.0f},{cx2:.0f}] '
                f'raw={[b["text"] for b in col_blocks]} -> names={col_names}'
            )

            if ctype == 'queue':
                for n in col_names:
                    if n and n not in queue_names:
                        queue_names.append(n)

        # 兜底：全图碎片字符级匹配找回漏网之鱼
        if known_names:
            all_text = ''.join(b['text'] for b in blocks)
            all_chars = set(all_text)
            for ref_name in known_names:
                if ref_name in queue_names: continue
                rc = set(ref_name)
                hit = all_chars & rc
                if len(hit) >= max(2, len(rc) * 0.5):
                    # 二次确认：尝试匹配每个碎片
                    for b in blocks:
                        if fuzzy_match_name(b['text'], known_names) == ref_name:
                            if ref_name not in queue_names:
                                queue_names.append(ref_name)
                            break

        debug_columns = '\n'.join(debug_col_lines)

        print(f'[Faculty-OCR] {len(merged_cols)} columns, first_role_col={first_role_col_idx}')
        print(f'[Faculty-OCR] Queue names ({len(queue_names)}): {queue_names}')

        os.unlink(pre)
        roster_text = '\n'.join(queue_names) if queue_names else ''
        return roster_text, debug_all_text, debug_columns

    finally:
        try: os.unlink(ip)
        except: pass


def inject_css():
    st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden}
    .stApp {background-color: #f0f2f5}
    .block-container {padding-top: 1rem !important}
    h1 {font-size: 1.8rem !important; font-weight: 700 !important}
    h2 {font-size: 1.3rem !important; font-weight: 600 !important}
    h3 {font-size: 1.1rem !important; font-weight: 600 !important; margin-top: 1rem !important}
    .stButton button {
        font-weight: 600 !important; border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important; transition: all 0.2s;
    }
    .stButton button:hover {transform: scale(1.02)}
    .stDownloadButton button {
        font-weight: 600 !important; border-radius: 10px !important;
        background-color: #16a34a !important; color: white !important;
        width: 100% !important; padding: 0.8rem !important;
    }
    div[data-testid="stMetricValue"] {font-size: 2rem !important; font-weight: 700 !important}
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# Pages
# ═══════════════════════════════════════════════════════════════

def go_to(page):
    st.session_state.page = page
    st.rerun()


# ── 首页 ──
def page_home():
    inject_css()

    st.markdown("""
    <div style="text-align:center; padding: 20px 0 30px 0">
        <h1>🎖️ 浙江大学国旗仪仗队 · 礼服自动分配系统</h1>
        <p style="color:#6b7280; font-size:15px; margin-top:8px">选择分配模式开始使用</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("### 🌄 日常升旗班礼服分配")
            st.caption("上传上月 Excel + 拍照上传排班表 → 自动检测共享冲突 → 重分配 → 下载")
            if st.button("进入", key="go_daily", use_container_width=True):
                go_to('daily')

    with col2:
        with st.container(border=True):
            st.markdown("### 🎓 院系升旗礼服分配")
            st.caption("输入队列人员名单 → 按尺寸排序 → 自动冲突检测 → 下载 4-sheet Excel")
            if st.button("进入", key="go_faculty", use_container_width=True):
                go_to('faculty')

    st.markdown("""
    <div style="text-align:center; padding:30px; color:#9ca3af; font-size:12px">
        浙江大学国旗仪仗队 &copy; 2026
    </div>
    """, unsafe_allow_html=True)


# ── 日常升旗页 ──
def page_daily():
    inject_css()

    st.markdown('<div style="margin-bottom:8px">', unsafe_allow_html=True)
    if st.button("← 返回首页", key="daily_back"):
        go_to('home')
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 🌄 日常升旗班礼服分配")
    st.caption("上传上月分配表 + 拍照上传排班表 → 自动检测冲突 → 下载新表")

    # Step 1: 上传 Excel
    st.markdown("#### ① 上传上月分配表 (.xlsx)")
    excel_file = st.file_uploader("拖拽或点击上传上月 Excel", type=['xlsx'],
                                   key="daily_excel", label_visibility="collapsed")

    # Step 2: 排班输入
    st.markdown("#### ② 拍照上传排班表")
    image_file = st.file_uploader("上传排班表照片（手写也可以）", type=['png','jpg','jpeg','webp'],
                                   key="daily_image", label_visibility="collapsed")
    st.caption("或手动输入/修正排班文字")

    schedule_text = st.text_area(
        "排班文字",
        placeholder="周一：李诗诗、郭婷心、岳佳凝、江文欣\n周二：柯天翊、章芮容、余佳卉、马欣雅\n周三：李泽一、方佳瑶、纪博雅、董欢瑶\n周四：林珩、王雨梦、施东隅、艾克达\n周五：吴桐、段茗萱、张艺、许诺",
        key="daily_schedule_text",
        label_visibility="collapsed",
        height=140
    )

    # OCR 提示
    ocr_warning = st.empty()

    # 生成按钮
    can_generate = excel_file is not None and (schedule_text.strip() or image_file is not None)
    gen_btn = st.button("🚀 生成本月分配表", key="daily_gen", use_container_width=True, disabled=not can_generate)

    if gen_btn and excel_file:
        with st.spinner("正在处理..."):
            try:
                excel_bytes = excel_file.read()
                ocr_parsed = ''

                if image_file:
                    img_bytes = image_file.read()
                    if len(img_bytes) > 0:
                        ocr_parsed = ocr_daily_schedule(img_bytes, excel_bytes)
                        if ocr_parsed:
                            schedule_text = ocr_parsed
                            ocr_warning.info("⚠️ OCR 识别结果已填入下方，请核对修正后再点生成")

                if not schedule_text.strip():
                    st.error("请提供排班文本或上传排班照片")
                    st.stop()

                schedule = parse_schedule(schedule_text.strip())
                if not schedule:
                    st.error(f"排班格式无法解析。当前内容:\n{schedule_text[:300]}")
                    st.stop()

                import openpyxl
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as t:
                    t.write(excel_bytes); tmp = t.name

                try:
                    wb = openpyxl.load_workbook(tmp)
                    persons = parse_equipment_sheet(wb['装备分配'])
                    rels = parse_shared_relations(persons)
                    mrels = merge_relations(rels)
                    conflicts = detect_conflicts(schedule, mrels)
                    pool = build_pool(wb)
                    reassigns, changed = resolve(conflicts, persons, schedule, pool)
                    b64 = generate_excel(tmp, persons, changed)

                    # ── 显示结果 ──
                    st.markdown("---")
                    st.markdown("### ③ 生成结果")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("冲突数", len(conflicts))
                    c2.metric("重分配", len(reassigns))
                    c3.metric("受影响人数", len(set(r['person'] for r in reassigns)))

                    if conflicts:
                        st.markdown("#### 冲突详情")
                        st.dataframe(
                            [{"日期": c['day'], "装备": '礼服' if c['item_type']=='uniform' else '礼帽',
                              "编号": c['item_code'], "需变动": c['person_to_move'],
                              "保留": c['person_to_keep']} for c in conflicts],
                            use_container_width=True, hide_index=True
                        )

                    if reassigns:
                        st.markdown("#### 重分配方案")
                        st.dataframe(
                            [{"姓名": r['person'], "装备": '礼服' if r['item_type']=='uniform' else '礼帽',
                              "旧编号": r['old_item'], "新编号": r['new_item']} for r in reassigns],
                            use_container_width=True, hide_index=True
                        )

                    st.download_button(
                        label="📥 下载本月分配表 (.xlsx)",
                        data=base64.b64decode(b64),
                        file_name="本月礼服分配.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    if ocr_parsed:
                        st.text_area("OCR 识别结果（可复制到上方修正）", value=ocr_parsed, height=120, key="daily_ocr_result")

                finally:
                    os.unlink(tmp)

            except Exception as e:
                import traceback
                st.error(f"生成失败: {e}")
                with st.expander("详细错误"):
                    st.code(traceback.format_exc())


# ── 院系升旗页 ──
def page_faculty():
    inject_css()

    st.markdown('<div style="margin-bottom:8px">', unsafe_allow_html=True)
    if st.button("← 返回首页", key="faculty_back"):
        go_to('home')
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 🎓 院系升旗礼服分配")
    st.caption("输入队列人员 → 按尺寸排序 → 冲突检测 → 下载 4-sheet Excel")

    # Step 1: 上传 Excel
    st.markdown("#### ① 上传礼服库存表 (.xlsx)")
    excel_file = st.file_uploader("上传包含所有人员装备信息的 Excel", type=['xlsx'],
                                   key="faculty_excel", label_visibility="collapsed")

    # Step 2: 上传照片 / 手动输入
    st.markdown("#### ② 拍照上传人员安排表")
    image_file = st.file_uploader("上传人员安排表照片（手写也可以）", type=['png','jpg','jpeg','webp'],
                                   key="faculty_image", label_visibility="collapsed")
    st.caption("AI 自动识别队列人员（总负责/场控/后勤/摄影不参与分配）")
    st.caption("或手动输入/修正队列人员（每行一人或顿号分隔）")

    # OCR 回填：渲染前从独立 session_state key 读取
    ocr_default = st.session_state.get('ocr_roster_result', '')
    ocr_meta_default = st.session_state.get('ocr_meta_result', {})

    roster_text = st.text_area(
        "队列人员",
        placeholder="林珩\n韩雅丽\n艾克达\n张鹏\n夏瑞泽\n戴傲\n叶宇轩",
        key="faculty_roster",
        label_visibility="collapsed",
        height=130,
        value=ocr_default
    )

    ocr_warning2 = st.empty()

    # 其他角色（可选）
    with st.expander("其他角色（可选，不参与分配）"):
        c1, c2 = st.columns(2)
        meta1 = c1.text_area("总负责", key="f_meta1", height=52, placeholder="（可选）",
                             value=ocr_meta_default.get('总负责', ''))
        meta2 = c2.text_area("场控", key="f_meta2", height=52, placeholder="（可选）",
                             value=ocr_meta_default.get('场控', ''))
        c3, c4 = st.columns(2)
        meta3 = c3.text_area("后勤", key="f_meta3", height=52, placeholder="（可选）",
                             value=ocr_meta_default.get('后勤', ''))
        meta4 = c4.text_area("摄影", key="f_meta4", height=52, placeholder="（可选）",
                             value=ocr_meta_default.get('摄影', ''))

    # 生成按钮
    can_gen = excel_file is not None and (roster_text.strip() or image_file is not None)
    gen_btn = st.button("🔍 预览排序 & 生成分配表", key="faculty_gen", use_container_width=True, disabled=not can_gen)

    if gen_btn and excel_file:
        with st.spinner("正在处理..."):
            try:
                excel_bytes = excel_file.read()
                ocr_parsed = ''

                ocr_debug_raw = ''
                ocr_debug_columns = ''
                if image_file:
                    # 先清空所有旧 OCR 缓存 & widget key
                    st.session_state.pop('ocr_roster_result', None)
                    st.session_state.pop('ocr_meta_result', None)
                    st.session_state.pop('ocr_pending', None)
                    for k in ['faculty_roster', 'f_meta1', 'f_meta2', 'f_meta3', 'f_meta4']:
                        st.session_state.pop(k, None)

                    img_bytes = image_file.read()
                    if len(img_bytes) > 0:
                        ocr_parsed, ocr_debug_raw, ocr_debug_columns = ocr_faculty_roster(img_bytes, excel_bytes)
                        if ocr_parsed:
                            # 直接覆盖，禁止与旧名单拼接
                            st.session_state.ocr_roster_result = ocr_parsed
                            st.session_state.ocr_meta_result = {}
                            st.session_state.ocr_pending = True
                            ocr_warning2.info("⚠️ OCR 识别结果已填入下方，请核对修正后再点生成")
                            st.rerun()
                        else:
                            ocr_warning2.warning("OCR 未识别到任何队列人员，请手动输入或重新拍照")

                # rerun 后 OCR 结果已回填，直接用 session_state 中的值
                if 'ocr_pending' in st.session_state:
                    roster_text = st.session_state.ocr_roster_result
                    st.session_state.pop('ocr_pending', None)
                if not roster_text.strip():
                    st.error("请提供队列人员名单或上传照片")
                    st.stop()

                # 解析队列人员姓名
                queue_names = []
                for chunk in re.split(r'[、，,\n\s]+', roster_text.strip()):
                    n = chunk.strip()
                    if len(n) >= 2: queue_names.append(n)

                # 其他角色
                meta_people = {}
                for label, val in [('总负责', meta1), ('场控', meta2), ('后勤', meta3), ('摄影', meta4)]:
                    if val.strip():
                        names = [n.strip() for n in re.split(r'[、，,\n\s]+', val.strip()) if len(n.strip()) >= 2]
                        if names: meta_people[label] = names

                import openpyxl
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as t:
                    t.write(excel_bytes); tmp = t.name

                try:
                    wb = openpyxl.load_workbook(tmp)
                    all_persons = parse_equipment_sheet(wb['装备分配'])
                    name_map = {p['name']: p for p in all_persons}
                    pool = build_pool(wb)

                    faculty_persons = []
                    missing = []
                    for name in queue_names:
                        p = name_map.get(name)
                        if p: faculty_persons.append(dict(p))
                        else: missing.append(name)

                    original_equip = {}
                    for p in faculty_persons:
                        for k in ['uniform', 'hat', 'boots', 'belt']:
                            original_equip[f'{p["name"]}|{k}'] = p.get(k, '')

                    conflicts = detect_faculty_conflicts(faculty_persons)
                    reassigns, changed = resolve_faculty_conflicts(conflicts, faculty_persons, pool)
                    b64 = generate_faculty_excel(faculty_persons, changed)
                    sorted_persons = sort_people_by_uniform(faculty_persons)

                    # ── 显示结果 ──
                    st.markdown("---")
                    st.markdown("### ③ 生成结果")

                    msg = f"生成完成: {len(faculty_persons)} 人, {len(conflicts)} 个冲突, {len(reassigns)} 个重分配"
                    if missing: msg += f"（{len(missing)} 人未在库存中找到）"
                    st.success(msg)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("冲突数", len(conflicts))
                    c2.metric("重分配", len(reassigns))
                    c3.metric("受影响人数", len(set(r['person'] for r in reassigns)))

                    # 排序后人员列表
                    st.markdown("#### 排序后人员列表")
                    rows = []
                    for i, p in enumerate(sorted_persons):
                        ch = changed.get(p['name'], {})
                        rows.append({
                            "序号": i+1, "姓名": p['name'],
                            "性别": '女' if p['gender']=='F' else '男',
                            "礼服": p.get('uniform',''),
                            "礼帽": p.get('hat',''),
                            "马靴": p.get('boots',''),
                            "腰带": p.get('belt',''),
                            "变更": '；'.join(f'{t}→{nv}' for t,nv in ch.items()) if ch else ''
                        })
                    st.dataframe(rows, use_container_width=True, hide_index=True)

                    if conflicts:
                        st.markdown("#### 冲突详情")
                        st.dataframe(
                            [{"装备类型": {'uniform':'礼服','hat':'礼帽','boots':'马靴','belt':'腰带'}.get(c['item_type'], c['item_type']),
                              "编号": c['item_code'], "需变动": c['person_to_move'],
                              "保留": c['person_to_keep']} for c in conflicts],
                            use_container_width=True, hide_index=True
                        )

                    if reassigns:
                        st.markdown("#### 重分配方案")
                        st.dataframe(
                            [{"姓名": r['person'],
                              "装备": {'uniform':'礼服','hat':'礼帽','boots':'马靴','belt':'腰带'}.get(r['item_type'], r['item_type']),
                              "旧编号": r['old_item'], "新编号": r['new_item']} for r in reassigns],
                            use_container_width=True, hide_index=True
                        )

                    st.download_button(
                        label="📥 下载礼服分配表 (.xlsx)",
                        data=base64.b64decode(b64),
                        file_name="院系升旗礼服分配.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    if ocr_parsed:
                        st.text_area("OCR 识别结果（可复制到上方修正）", value=ocr_parsed, height=120, key="faculty_ocr_result")
                    if ocr_debug_raw:
                        st.text_area("调试-OCR原始文本", value=ocr_debug_raw, height=120, key="faculty_debug_raw")
                    if ocr_debug_columns:
                        st.text_area("调试-列聚类结果", value=ocr_debug_columns, height=120, key="faculty_debug_cols")

                finally:
                    os.unlink(tmp)

            except Exception as e:
                import traceback
                st.error(f"生成失败: {e}")
                with st.expander("详细错误"):
                    st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# Main Router
# ═══════════════════════════════════════════════════════════════
if st.session_state.page == 'home':
    page_home()
elif st.session_state.page == 'daily':
    page_daily()
elif st.session_state.page == 'faculty':
    page_faculty()
