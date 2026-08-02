"""礼服分配系统 - Flask版，双击启动.bat 即可使用"""
import base64, io, os, re, tempfile
from flask import Flask, request, jsonify
from difflib import SequenceMatcher

app = Flask(__name__)

YELLOW = 'FFFFFF00'
PORT = 8765

# ── 人名模糊匹配 + 自动修正 ──
def fuzzy_match(ocr_name, known_names):
    """将 OCR 误识别的名字匹配到最接近的已知人名"""
    if not known_names:
        return ocr_name
    if ocr_name in known_names:
        return ocr_name
    # 去掉 OCR 噪声字符
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
    return re.sub(r'[_|^~\s\d]+', '', ocr_name)  # 至少去噪

# ── 业务逻辑 ──
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
    """为冲突人员寻找最接近原尺寸的替换装备。

    礼服评分规则（尺寸档位对齐）：
      - 身高每差 5cm = 一个档位，权重 4 → 跨一档 ≈ 20分
      - 胸围每差 4cm = 一个档位，权重 5 → 跨一档 ≈ 20分
      - 两个维度等权重，确保选到整体最合身的替代品
    礼帽评分：号码差值直接比较。
    """
    own = person[item_type]
    available = [x for x in all_items if x not in used_items and x != own]
    gender = person['gender']
    candidates = []
    for item in available:
        if item_type == 'uniform':
            info = parse_uniform_code(item)
            if not info or info['gender'] != gender: continue
            pi = parse_uniform_code(own) or dict(height=0, chest=0)
            # 身高每cm计4分，胸围每cm计5分 → 一档身高(5cm)≈一档胸围(4cm)≈20分
            score = abs(info['height'] - pi['height']) * 4 + abs(info['chest'] - pi['chest']) * 5
            candidates.append((score, item))
        elif item_type == 'hat':
            info = parse_hat_code(item)
            if not info or info['gender'] != gender: continue
            pi = parse_hat_code(own) or dict(number=0)
            candidates.append((abs(info['number'] - pi['number']), item))
        else:
            # 马靴、腰带等非尺寸装备，任意同性别即可
            if item.startswith(gender):
                candidates.append((0, item))

    # 如果同性别实在没有，放宽到任意性别
    if not candidates:
        for item in available:
            candidates.append((999998, item))
    # 兜底：任意可用
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
            if re.search(pat, line):
                day = label; break
        if not day: continue
        rest = re.sub(r'周\s*[一二三四五]\s*[:：]?\s*', '', line)
        chunks = re.split(r'[、，,]', rest)
        names = []
        for chunk in chunks:
            n = re.sub(r'\s+', '', chunk)
            if len(n) >= 2:
                names.append(n)
        if names:
            schedule.append(dict(day=day, people=names))
    return schedule

# ── 院系升旗礼服分配 ──
def uniform_sort_key(person):
    """返回排序元组: (性别序, 身高, 胸围, 序号)
    女(F)在前=0, 男(M)在后=1，空装备排最后=2"""
    suit = person.get('uniform', '')
    if not suit:
        return (2, 999, 999, 999)
    gender_code = 0 if suit.startswith('F') else 1
    nums = [int(n) for n in re.findall(r'\d+', suit)]
    while len(nums) < 3:
        nums.append(0)
    return (gender_code, nums[0], nums[1], nums[2])

def sort_people_by_uniform(people):
    """院系升旗排序：女在前男在后，同性别内尺寸从小到大"""
    return sorted(people, key=uniform_sort_key)

def detect_faculty_conflicts(persons):
    """检测队列内的装备冲突：同一件装备被多人使用即冲突"""
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
    """解决队列内的装备冲突，为冲突者找最接近尺寸的替换品"""
    reassigns, changed = [], {}
    # 当前队列所有人正在用的装备
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

FACULTY_TEMPLATE = r'C:\Users\夏瑞泽\xwechat_files\wxid_vnl456wm0r9h12_0c22\msg\file\2026-07\26.4.27管理学院院系升旗装备分配表.xlsx'

def generate_faculty_excel(persons, changed):
    """基于模板修改数据，不自己设计样式。

    用 openpyxl 打开 FACULTY_TEMPLATE，只清空 Sheet1 数据行并重写。
    Sheet2/3/4 保持模板原样不动。
    """
    import openpyxl
    from openpyxl.styles import PatternFill

    wb = openpyxl.load_workbook(FACULTY_TEMPLATE)
    yellow_fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')

    sorted_persons = sort_people_by_uniform(persons)

    # ═══════════════════════════════════════════════════════════
    # Sheet 1: 装备分配 — 清空旧数据，写入新数据
    # ═══════════════════════════════════════════════════════════
    ws1 = wb['装备分配']

    # 只清空数据行的值（不重设字体/边框/对齐）
    for row in range(2, ws1.max_row + 1):
        for col in range(1, 7):
            ws1.cell(row=row, column=col).value = None

    # 写入排序后的人员（只 set value）
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

    # 清空多余行
    for row in range(len(sorted_persons) + 2, ws1.max_row + 1):
        for col in range(1, 7):
            ws1.cell(row=row, column=col).value = None

    # ═══════════════════════════════════════════════════════════
    # Sheet 2-4: 保持模板原样，不做任何修改
    # ═══════════════════════════════════════════════════════════

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ── 院系升旗页面 ──
FACULTY_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>院系升旗礼服分配</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif;background:#f0f2f5;color:#374151;min-height:100vh}
header{background:#fff;border-bottom:1px solid #e5e7eb;padding:16px 0;text-align:center}
header a{color:#2563eb;text-decoration:none;font-size:13px;position:absolute;left:24px;top:18px}
h1{font-size:22px;font-weight:700}
header p{color:#6b7280;margin-top:4px;font-size:13px}
main{max-width:860px;margin:32px auto;padding:0 24px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;margin-bottom:20px}
.card h2{font-size:16px;display:flex;align-items:center;gap:8px;margin-bottom:16px}
.badge{width:26px;height:26px;border-radius:50%;background:#2563eb;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
label.block{display:block;font-weight:600;margin-bottom:6px;margin-top:14px;font-size:14px}
label.block:first-child{margin-top:0}
textarea{width:100%;height:130px;border:1px solid #e5e7eb;border-radius:8px;padding:12px;font:13px Consolas,'Microsoft YaHei',monospace;resize:vertical}
.up{border:2px dashed #e5e7eb;border-radius:10px;padding:28px;text-align:center;cursor:pointer;transition:.2s}
.up:hover{border-color:#2563eb;background:#eff6ff}
.up.sel{border-color:#16a34a;background:#f0fdf4}
.up input{display:none}
.up .n{font-weight:600;color:#16a34a;margin-top:4px;display:none}
.or{display:flex;align-items:center;gap:12px;margin:14px 0}.or hr{flex:1;border:none;border-top:1px solid #e5e7eb}.or span{color:#9ca3af;font-size:13px}
.btn{width:100%;padding:14px;border:none;border-radius:10px;font-size:17px;font-weight:600;cursor:pointer;transition:.2s}
.btn-b{background:#2563eb;color:#fff}.btn-b:hover{background:#1d4ed8}.btn-b:disabled{background:#d1d5db;cursor:not-allowed}
.btn-g{background:#16a34a;color:#fff}.btn-g:hover{background:#15803d}.btn-g:disabled{background:#d1d5db;cursor:not-allowed}
.spin{width:20px;height:20px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:s .6s linear infinite}@keyframes s{to{transform:rotate(360deg)}}
.roles{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.st{padding:16px;border-radius:10px;text-align:center}
.st.c{background:#fffbeb;border:1px solid #fde68a}.st.r{background:#eff6ff;border:1px solid #bfdbfe}.st.p{background:#f0fdf4;border:1px solid #bbf7d0}
.st b{font-size:28px;display:block}.st span{color:#6b7280;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
th{background:#f9fafb;padding:6px 8px;text-align:center;font-weight:600;border:1px solid #e5e7eb}
td{padding:6px 8px;border:1px solid #e5e7eb;text-align:center}
.old{text-decoration:line-through;color:#9ca3af;font-size:12px}
.hl{background:#fef9c3;font-weight:600;font-size:12px}
.err{background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;color:#ef4444;display:none;margin-top:12px}
#load{text-align:center;padding:40px;display:none}
footer{text-align:center;padding:24px;color:#9ca3af;font-size:12px}
</style>
</head>
<body>
<header>
<a href="/">&#8592; 返回首页</a>
<h1>&#127891; 院系升旗礼服分配</h1>
<p>输入队列人员 → 按尺寸排序 → 冲突检测 → 下载</p>
</header>
<main>

<div class="card">
<h2><span class="badge">1</span> 上传礼服库存表 (.xlsx)</h2>
<div class="up" id="ea"><div style="font-size:36px;margin-bottom:8px">&#128206;</div><div>上传包含所有人员装备信息的Excel</div><div style="color:#9ca3af;font-size:13px">系统将从中提取装备库存</div>
<input type="file" id="ei" accept=".xlsx"/><div class="n" id="en"></div></div>
</div>

<div class="card">
<h2><span class="badge">2</span> 拍照上传人员安排表</h2>
<div class="up" id="ia"><div style="font-size:36px;margin-bottom:8px">&#128247;</div><div>点击上传人员安排表照片（手写也可以）</div><div style="color:#9ca3af;font-size:13px">AI自动识别队列人员姓名</div>
<input type="file" id="ii" accept="image/*"/><div class="n" id="inm"></div></div>
<div class="hint" id="ohint" style="display:none;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;margin-top:10px;font-size:13px;color:#92400e;">&#9888; OCR识别结果已填入下方，请核对修正后再点生成</div>
<div class="or"><hr><span>或手动输入/修正队列人员</span><hr></div>
<p style="color:#6b7280;font-size:13px;margin-bottom:8px">每行一人或顿号分隔。总负责、场控、后勤、摄影不参与分配。</p>
<textarea id="rp" placeholder="林珩&#10;韩雅丽&#10;艾克达&#10;张鹏&#10;夏瑞泽&#10;戴傲&#10;叶宇轩"></textarea>
<div class="roles">
<div><label class="block">总负责</label><textarea id="r1" rows="2" placeholder="（可选，不参与分配）"></textarea></div>
<div><label class="block">场控</label><textarea id="r2" rows="2" placeholder="（可选，不参与分配）"></textarea></div>
<div><label class="block">后勤</label><textarea id="r3" rows="2" placeholder="（可选，不参与分配）"></textarea></div>
<div><label class="block">摄影</label><textarea id="r4" rows="2" placeholder="（可选，不参与分配）"></textarea></div>
</div>
</div>

<button class="btn btn-b" id="gb" disabled>&#128269; 预览排序 &amp; 生成分配表</button>

<div class="err" id="er"></div>
<div id="load"><div class="spin" style="display:inline-block;border-color:#d1d5db;border-top-color:#2563eb;width:32px;height:32px"></div><p style="margin-top:12px;color:#6b7280">正在处理...</p></div>

<div id="res" style="display:none"><div class="card">
<h2><span class="badge">3</span> 生成结果</h2>
<p style="color:#6b7280;margin-bottom:16px" id="rm"></p>
<div class="stats" id="sr" style="display:none">
<div class="st.c"><b id="cc">0</b><span>冲突数</span></div>
<div class="st.r"><b id="rc">0</b><span>重分配</span></div>
<div class="st p"><b id="ac">0</b><span>受影响人数</span></div>
</div>
<div id="pt"></div>
<div id="rt"></div>
<div style="margin-top:20px"><button class="btn btn-g" id="db" disabled>&#128229; 下载礼服分配表 (.xlsx)</button></div>
</div></div>
</main>
<footer>浙江大学国旗仪仗队 &copy; 2026</footer>
<script>
var ef=null,imgf=null,xb64='';
function ua(id,inpId,nmId,cb){
  var a=document.getElementById(id),inp=document.getElementById(inpId),nm=document.getElementById(nmId);
  a.addEventListener('click',function(){inp.click()});
  a.addEventListener('dragover',function(e){e.preventDefault()});
  a.addEventListener('drop',function(e){e.preventDefault();var f=e.dataTransfer.files[0];if(f)cb(f,a,nm)});
  inp.addEventListener('change',function(){var f=inp.files[0];if(f)cb(f,a,nm)});
}
function sf(f,a,nm){a.classList.add('sel');nm.style.display='block';nm.textContent=f.name;chk()}
ua('ea','ei','en',function(f,a,nm){ef=f;sf(f,a,nm)});
ua('ia','ii','inm',function(f,a,nm){imgf=f;sf(f,a,nm);document.getElementById('ohint').style.display='block'});
document.getElementById('rp').addEventListener('input',chk);
function chk(){
  var roster = document.getElementById('rp').value.trim();
  document.getElementById('gb').disabled=!(ef && (roster || imgf));
}
document.getElementById('gb').addEventListener('click',async function(){
  if(!ef)return;
  document.getElementById('er').style.display='none';
  document.getElementById('res').style.display='none';
  document.getElementById('load').style.display='block';
  document.getElementById('gb').disabled=true;
  try{
    var fd=new FormData();
    fd.append('excel',ef);
    fd.append('roster',document.getElementById('rp').value.trim());
    if(imgf)fd.append('image',imgf);
    // 附送其他角色（仅记录，不参与分配）
    var meta = ['总负责','场控','后勤','摄影'];
    for(var i=1;i<=4;i++){
      var v = document.getElementById('r'+i).value.trim();
      if(v) fd.append('meta_'+i, v);
    }
    var r=await fetch('/generate-faculty',{method:'POST',body:fd});
    if(!r.ok){var t=await r.text();throw new Error(t.substring(0,500))}
    show(await r.json());
  }catch(e){
    document.getElementById('er').textContent='生成失败: '+e.message;
    document.getElementById('er').style.display='block';
  }
  document.getElementById('load').style.display='none';chk();
});
function show(d){
  document.getElementById('res').style.display='block';
  document.getElementById('rm').textContent=d.message;
  document.getElementById('sr').style.display='grid';
  document.getElementById('cc').textContent=d.conflicts_count;
  document.getElementById('rc').textContent=d.reassignments_count;
  document.getElementById('ac').textContent=new Set(d.reassignments.map(function(r){return r.person})).size;
  // OCR结果回填
  if(d.ocr_text){
    document.getElementById('rp').value=d.ocr_text;
    document.getElementById('ohint').style.display='block';
  }
  // 其他角色自动填入
  if(d.meta_people){
    if(d.meta_people['总负责']) document.getElementById('r1').value=d.meta_people['总负责'].join('\n');
    if(d.meta_people['场控']) document.getElementById('r2').value=d.meta_people['场控'].join('\n');
    if(d.meta_people['后勤']) document.getElementById('r3').value=d.meta_people['后勤'].join('\n');
    if(d.meta_people['摄影']) document.getElementById('r4').value=d.meta_people['摄影'].join('\n');
  }
  xb64=d.excel_base64;
  document.getElementById('db').disabled=false;
  document.getElementById('db').onclick=function(){
    var b=atob(xb64),u8=new Uint8Array(b.length);
    for(var i=0;i<b.length;i++)u8[i]=b.charCodeAt(i);
    var blob=new Blob([u8],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='院系升旗礼服分配.xlsx';a.click();
  };
  // 预览表格
  var h='<h3 style="margin:12px 0 4px">排序后人员列表</h3><table><tr><th>序号</th><th>姓名</th><th>性别</th><th>礼服</th><th>礼帽</th><th>马靴</th><th>腰带</th></tr>';
  d.sorted_persons.forEach(function(p,i){
    var ch = d.changes[p.name] || {};
    h+='<tr>';
    h+='<td>'+(i+1)+'</td>';
    h+='<td><b>'+p.name+'</b></td>';
    h+='<td>'+(p.gender==='F'?'女':'男')+'</td>';
    ['uniform','hat','boots','belt'].forEach(function(k){
      var v = p[k]||'';
      var cls = ch[k] ? 'hl' : '';
      var oldv = ch[k] ? '<br><span class=old>'+d.original_equip[p.name+'|'+k]+'→</span>' : '';
      h+='<td class='+cls+'>'+v+oldv+'</td>';
    });
    h+='</tr>';
  });
  h+='</table>';
  document.getElementById('pt').innerHTML=h;
  // 冲突&重分配
  if(d.conflicts.length){
    h='<h3 style="margin:12px 0 4px">冲突详情</h3><table><tr><th>装备类型</th><th>编号</th><th>需变动</th><th>保留</th></tr>';
    d.conflicts.forEach(function(c){h+='<tr><td>'+c.item_type+'</td><td>'+c.item_code+'</td><td>'+c.person_to_move+'</td><td>'+c.person_to_keep+'</td></tr>'});
    h+='</table>';
  }
  if(d.reassignments.length){
    h+='<h3 style="margin:12px 0 4px">重分配方案</h3><table><tr><th>姓名</th><th>装备</th><th>旧编号</th><th>新编号</th></tr>';
    d.reassignments.forEach(function(r){h+='<tr><td>'+r.person+'</td><td>'+r.item_type+'</td><td class=old>'+r.old_item+'</td><td class=hl>'+r.new_item+'</td></tr>'});
    h+='</table>';
  }
  document.getElementById('rt').innerHTML=h;
  document.getElementById('res').scrollIntoView({behavior:'smooth'});
}
</script>
</body></html>'''

# ── 日常升旗页面（从旧首页移过来）──
DAILY_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>日常升旗班礼服分配</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif;background:#f0f2f5;color:#374151;min-height:100vh}
header{background:#fff;border-bottom:1px solid #e5e7eb;padding:16px 0;text-align:center}
header a{color:#2563eb;text-decoration:none;font-size:13px;position:absolute;left:24px;top:18px}
h1{font-size:22px;font-weight:700}
header p{color:#6b7280;margin-top:4px;font-size:13px}
main{max-width:860px;margin:32px auto;padding:0 24px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;margin-bottom:20px}
.card h2{font-size:16px;display:flex;align-items:center;gap:8px;margin-bottom:16px}
.badge{width:26px;height:26px;border-radius:50%;background:#2563eb;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
.up{border:2px dashed #e5e7eb;border-radius:10px;padding:32px;text-align:center;cursor:pointer;transition:.2s}
.up:hover{border-color:#2563eb;background:#eff6ff}
.up.sel{border-color:#16a34a;background:#f0fdf4}
.up input{display:none}
.up .n{font-weight:600;color:#16a34a;margin-top:4px;display:none}
textarea{width:100%;height:180px;border:1px solid #e5e7eb;border-radius:8px;padding:12px;font:13px Consolas,'Microsoft YaHei',monospace;resize:vertical}
.or{display:flex;align-items:center;gap:12px;margin:16px 0}.or hr{flex:1;border:none;border-top:1px solid #e5e7eb}.or span{color:#9ca3af;font-size:13px}
.btn{width:100%;padding:14px;border:none;border-radius:10px;font-size:17px;font-weight:600;cursor:pointer;transition:.2s}
.btn-b{background:#2563eb;color:#fff}.btn-b:hover{background:#1d4ed8}.btn-b:disabled{background:#d1d5db;cursor:not-allowed}
.btn-g{background:#16a34a;color:#fff}.btn-g:hover{background:#15803d}.btn-g:disabled{background:#d1d5db;cursor:not-allowed}
.spin{width:20px;height:20px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:s .6s linear infinite}@keyframes s{to{transform:rotate(360deg)}}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.st{padding:16px;border-radius:10px;text-align:center}
.st.c{background:#fffbeb;border:1px solid #fde68a}.st.r{background:#eff6ff;border:1px solid #bfdbfe}.st.p{background:#f0fdf4;border:1px solid #bbf7d0}
.st b{font-size:28px;display:block}.st span{color:#6b7280;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}
th{background:#f9fafb;padding:8px 10px;text-align:left;font-weight:600;border-bottom:1px solid #e5e7eb}
td{padding:8px 10px;border-bottom:1px solid #f3f4f6}
.mv{color:#ef4444}.kp{color:#16a34a}.old{text-decoration:line-through;color:#9ca3af;font-size:12px}
.hl{background:#fef9c3;font-weight:600;font-size:12px}
.err{background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;color:#ef4444;display:none;margin-top:12px}
#load{text-align:center;padding:40px;display:none}
footer{text-align:center;padding:24px;color:#9ca3af;font-size:12px}
.hint{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;margin-top:10px;font-size:13px;color:#92400e;display:none}
</style>
</head>
<body>
<header>
<a href="/">&#8592; 返回首页</a>
<h1>&#127748; 日常升旗班礼服分配</h1>
<p>上传上月Excel + 拍照上传排班表 → 自动检测冲突 → 下载新表</p>
</header>
<main>
<div class="card">
<h2><span class="badge">1</span> 上传上月分配表 (.xlsx)</h2>
<div class="up" id="ea"><div style="font-size:36px;margin-bottom:8px">&#128206;</div><div>拖拽或点击上传上月 Excel</div><div style="color:#9ca3af;font-size:13px">支持 .xlsx 格式</div>
<input type="file" id="ei" accept=".xlsx"/><div class="n" id="en"></div></div>
</div>

<div class="card">
<h2><span class="badge">2</span> 拍照上传排班表</h2>
<div class="up" id="ia"><div style="font-size:36px;margin-bottom:8px">&#128247;</div><div>点击上传排班表照片（手写也可以）</div><div style="color:#9ca3af;font-size:13px">AI会自动识别手写名字</div>
<input type="file" id="ii" accept="image/*"/><div class="n" id="inm"></div></div>
<div class="hint" id="ohint">&#9888; OCR识别结果可能有误差，请在下方核对修正后再点生成</div>
<div class="or"><hr><span>或手动输入/修正排班文字</span><hr></div>
<textarea id="st" placeholder="周一：李诗诗、郭婷心、岳佳凝、江文欣&#10;周二：柯天翊、章芮容、余佳卉、马欣雅&#10;周三：李泽一、方佳瑶、纪博雅、董欢瑶&#10;周四：林珩、王雨梦、施东隅、艾克达&#10;周五：吴桐、段茗萱、张艺、许诺"></textarea>
</div>

<button class="btn btn-b" id="gb" disabled>&#128640; 生成本月分配表</button>
<div class="err" id="er"></div>
<div id="load"><div class="spin" style="display:inline-block;border-color:#d1d5db;border-top-color:#2563eb;width:32px;height:32px"></div><p style="margin-top:12px;color:#6b7280">AI正在识别手写排班表并生成分配方案...</p></div>

<div id="res" style="display:none"><div class="card">
<h2><span class="badge">3</span> 生成结果</h2>
<p style="color:#6b7280;margin-bottom:16px" id="rm"></p>
<div class="stats" id="sr" style="display:none">
<div class="st c"><b id="cc">0</b><span>冲突数</span></div>
<div class="st r"><b id="rc">0</b><span>重分配</span></div>
<div class="st p"><b id="ac">0</b><span>受影响人数</span></div>
</div>
<div id="ct"></div><div id="rt"></div>
<div style="margin-top:20px"><button class="btn btn-g" id="db" disabled>&#128229; 下载本月分配表 (.xlsx)</button></div>
</div></div>
</main>
<footer>浙江大学国旗仪仗队 &copy; 2026</footer>
<script>
var ef=null,imgf=null,xb64='';
function ua(id,inpId,nmId,cb,extra){
  var a=document.getElementById(id),inp=document.getElementById(inpId),nm=document.getElementById(nmId);
  a.addEventListener('click',function(){inp.click()});
  a.addEventListener('dragover',function(e){e.preventDefault()});
  a.addEventListener('drop',function(e){e.preventDefault();var f=e.dataTransfer.files[0];if(f)cb(f,a,nm,extra)});
  inp.addEventListener('change',function(){var f=inp.files[0];if(f)cb(f,a,nm,extra)});
}
function sf(f,a,nm){a.classList.add('sel');nm.style.display='block';nm.textContent=f.name;chk()}
ua('ea','ei','en',function(f,a,nm){ef=f;sf(f,a,nm)});
ua('ia','ii','inm',function(f,a,nm){imgf=f;sf(f,a,nm); document.getElementById('ohint').style.display='block'});
document.getElementById('st').addEventListener('input',chk);
function chk(){document.getElementById('gb').disabled=!(ef&&(document.getElementById('st').value.trim()||imgf))}
document.getElementById('gb').addEventListener('click',async function(){
  if(!ef)return;
  document.getElementById('er').style.display='none';
  document.getElementById('res').style.display='none';
  document.getElementById('load').style.display='block';
  document.getElementById('gb').disabled=true;
  try{
    var fd=new FormData();
    fd.append('excel',ef);
    fd.append('schedule',document.getElementById('st').value.trim());
    if(imgf)fd.append('image',imgf);
    var r=await fetch('/generate',{method:'POST',body:fd});
    if(!r.ok){var t=await r.text();throw new Error(t.substring(0,500))}
    show(await r.json());
  }catch(e){
    document.getElementById('er').textContent='生成失败: '+e.message;
    document.getElementById('er').style.display='block';
  }
  document.getElementById('load').style.display='none';chk();
});
function show(d){
  document.getElementById('res').style.display='block';
  document.getElementById('rm').textContent=d.message;
  document.getElementById('sr').style.display='grid';
  document.getElementById('cc').textContent=d.conflicts_count;
  document.getElementById('rc').textContent=d.reassignments_count;
  document.getElementById('ac').textContent=new Set(d.reassignments.map(function(r){return r.person})).size;
  if(d.ocr_text){
    document.getElementById('st').value=d.ocr_text;
    document.getElementById('ohint').style.display='block';
  }
  xb64=d.excel_base64;
  document.getElementById('db').disabled=false;
  document.getElementById('db').onclick=function(){
    var b=atob(xb64),u8=new Uint8Array(b.length);
    for(var i=0;i<b.length;i++)u8[i]=b.charCodeAt(i);
    var blob=new Blob([u8],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='本月礼服分配.xlsx';a.click();
  };
  var h='';
  if(d.conflicts.length){
    h+='<h3 style="margin:12px 0 4px">冲突详情</h3><table><tr><th>日期</th><th>装备</th><th>编号</th><th>需变动</th><th>保留</th></tr>';
    d.conflicts.forEach(function(c){h+='<tr><td>'+c.day+'</td><td>'+c.item_type+'</td><td style="font-size:12px">'+c.item_code+'</td><td class="mv">'+c.person_to_move+'</td><td class="kp">'+c.person_to_keep+'</td></tr>'});
    h+='</table>';
    document.getElementById('ct').innerHTML=h;
  }
  if(d.reassignments.length){
    h='<h3 style="margin:12px 0 4px">重分配方案</h3><table><tr><th>姓名</th><th>装备</th><th>旧编号</th><th>新编号</th></tr>';
    d.reassignments.forEach(function(r){h+='<tr><td>'+r.person+'</td><td>'+r.item_type+'</td><td class="old">'+r.old_item+'</td><td class="hl">'+r.new_item+'</td></tr>'});
    h+='</table>';
    document.getElementById('rt').innerHTML=h;
  }
  document.getElementById('res').scrollIntoView({behavior:'smooth'});
}
</script>
</body></html>'''
HOME_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>礼服自动分配系统</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif;background:#f0f2f5;color:#374151;min-height:100vh}
header{background:linear-gradient(135deg,#1a365d,#2563eb);color:#fff;padding:28px 0;text-align:center}
header h1{font-size:22px;font-weight:700}
header p{opacity:0.85;margin-top:6px;font-size:14px}
main{max-width:700px;margin:40px auto;padding:0 24px}
.entries{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.entry{background:#fff;border:2px solid #e5e7eb;border-radius:14px;padding:36px 24px;text-align:center;cursor:pointer;transition:.25s;text-decoration:none;color:inherit;display:block}
.entry:hover{border-color:#2563eb;transform:translateY(-3px);box-shadow:0 12px 32px rgba(37,99,235,.15)}
.entry .icon{font-size:48px;margin-bottom:12px}
.entry h2{font-size:18px;margin-bottom:8px}
.entry p{color:#6b7280;font-size:13px;line-height:1.6}
.badge-new{display:inline-block;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600;margin-left:6px}
footer{text-align:center;padding:24px;color:#9ca3af;font-size:12px}
</style>
</head>
<body>
<header>
<h1>&#127894; 浙江大学国旗仪仗队 · 礼服自动分配系统</h1>
<p>选择分配模式开始使用</p>
</header>
<main>
<div class="entries">
<a href="/daily" class="entry">
  <div class="icon">&#127748;</div>
  <h2>日常升旗班礼服分配</h2>
  <p>上传上月Excel + 拍照上传排班表<br>自动检测共享冲突 → 重分配 → 下载</p>
</a>
<a href="/faculty" class="entry">
  <div class="icon">&#127891;</div>
  <h2>院系升旗礼服分配 <span class="badge-new">NEW</span></h2>
  <p>输入队列人员名单<br>按尺寸排序 → 自动冲突检测 → 下载</p>
</a>
</div>
</main>
<footer>浙江大学国旗仪仗队 &copy; 2026</footer>
</body></html>'''

# ── Routes ──
@app.route('/')
def index():
    return HOME_HTML

@app.route('/daily')
def daily():
    return DAILY_HTML

@app.route('/faculty')
def faculty():
    return FACULTY_HTML

@app.route('/generate', methods=['POST'])
def generate():
    import openpyxl
    from openpyxl.styles import PatternFill

    excel_file = request.files.get('excel')
    if not excel_file:
        return '请上传 Excel 文件', 400

    excel_bytes = excel_file.read()
    schedule_text = request.form.get('schedule', '').strip()
    image_file = request.files.get('image')
    ocr_parsed_text = ''

    # ── OCR 图片（EasyOCR 手写中文识别）──
    if image_file and image_file.filename:
        img_bytes = image_file.read()
        if len(img_bytes) > 0:
            from PIL import Image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as t:
                t.write(img_bytes); ip = t.name
            try:
                img = Image.open(ip).convert('RGB')
                w, h = img.size
                print(f'[OCR] Image size: {w}x{h}')

                # 先从 Excel 加载已知人名
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as et:
                    et.write(excel_bytes); etmp = et.name
                try:
                    wb_tmp = openpyxl.load_workbook(etmp)
                    known_names = []
                    for row in range(2, wb_tmp['装备分配'].max_row + 1):
                        n = wb_tmp['装备分配'].cell(row=row, column=2).value
                        if n and str(n).strip():
                            known_names.append(str(n).strip())
                    wb_tmp.close()
                finally:
                    os.unlink(etmp)

                print(f'[OCR] Loaded {len(known_names)} known names')

                # EasyOCR 识别
                scale = max(1, 800 // w)
                img = img.resize((w * scale, h * scale), Image.LANCZOS)
                pre = ip + '_pre.png'; img.save(pre)

                import easyocr, numpy as np
                reader = easyocr.Reader(['ch_sim'], gpu=False)
                results = reader.readtext(np.array(img), detail=1)
                print(f'[OCR] Found {len(results)} text regions')

                # 分离日期标题和名字
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
                print(f'[OCR] Days detected: {[d["day"] for d in days_info]}')

                # 分组：每个名字分到最近的列
                grouped = {d['day']: [] for d in days_info}
                if days_info:
                    col_width = (days_info[-1]['x2'] - days_info[0]['x1']) / len(days_info)
                    for n in name_entries:
                        best_d, best_dist = None, 99999
                        for d in days_info:
                            dist = abs(n['x'] - d['cx'])
                            if dist < best_dist:
                                best_dist, best_d = dist, d
                        if best_d and best_dist < col_width * 1.3:
                            grouped[best_d['day']].append((n['y'], n['name']))

                # 去重 + 模糊匹配修正
                ocr_schedule = []
                total_fixed = 0
                for day_label, nl in grouped.items():
                    seen = set()
                    unique = []
                    for _, raw_name in sorted(nl):
                        corrected = fuzzy_match(raw_name, known_names)
                        if corrected != raw_name:
                            total_fixed += 1
                        if corrected not in seen and corrected in known_names:
                            seen.add(corrected); unique.append(corrected)
                    if unique:
                        ocr_schedule.append(dict(day=day_label, people=unique))

                if total_fixed > 0:
                    print(f'[OCR] Auto-corrected {total_fixed} OCR errors')

                os.unlink(pre)

                if ocr_schedule:
                    ocr_parsed_text = '\n'.join(
                        d['day'] + '：' + '、'.join(d['people']) for d in ocr_schedule
                    )
                    schedule_text = ocr_parsed_text
                    print(f'[OCR] Result: {len(ocr_schedule)} days, {sum(len(s["people"]) for s in ocr_schedule)} people')

            except Exception as e:
                import traceback
                print(f'[OCR ERROR] {e}')
                traceback.print_exc()
            finally:
                try: os.unlink(ip)
                except: pass

    if not schedule_text:
        return '请提供排班文本或上传排班照片（照片需要能看清文字）', 400

    schedule = parse_schedule(schedule_text)
    if not schedule:
        return f'排班格式无法解析，请检查格式。\n当前内容:\n{schedule_text[:300]}', 400

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

        return jsonify(
            success=True,
            message=f'生成完成: {len(conflicts)} 个冲突, {len(reassigns)} 个重分配',
            conflicts_count=len(conflicts),
            reassignments_count=len(reassigns),
            conflicts=[dict(day=c['day'],
                item_type='礼服' if c['item_type']=='uniform' else '礼帽',
                item_code=c['item_code'],
                person_to_move=c['person_to_move'],
                person_to_keep=c['person_to_keep']) for c in conflicts],
            reassignments=[dict(person=r['person'],
                item_type='礼服' if r['item_type']=='uniform' else '礼帽',
                old_item=r['old_item'], new_item=r['new_item']) for r in reassigns],
            excel_base64=b64,
            ocr_text=(ocr_parsed_text if image_file and image_file.filename else ''),
        )
    finally:
        os.unlink(tmp)


@app.route('/generate-faculty', methods=['POST'])
def generate_faculty():
    """院系升旗礼服分配"""
    import openpyxl

    excel_file = request.files.get('excel')
    if not excel_file:
        return '请上传礼服库存 Excel 文件', 400

    excel_bytes = excel_file.read()
    roster_text = request.form.get('roster', '').strip()
    image_file = request.files.get('image')
    ocr_parsed_text = ''

    # ── OCR 识别 ──
    if image_file and image_file.filename:
        img_bytes = image_file.read()
        if len(img_bytes) > 0:
            from PIL import Image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as t:
                t.write(img_bytes); ip = t.name
            try:
                img = Image.open(ip).convert('RGB')
                w, h = img.size
                print(f'[Faculty-OCR] Image size: {w}x{h}')

                # 从 Excel 加载已知人名
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as et:
                    et.write(excel_bytes); etmp = et.name
                try:
                    wb_tmp = openpyxl.load_workbook(etmp)
                    known_names = []
                    for row in range(2, wb_tmp['装备分配'].max_row + 1):
                        n = wb_tmp['装备分配'].cell(row=row, column=2).value
                        if n and str(n).strip():
                            known_names.append(str(n).strip())
                    wb_tmp.close()
                finally:
                    os.unlink(etmp)

                scale = max(1, 800 // w)
                img = img.resize((w * scale, h * scale), Image.LANCZOS)
                pre = ip + '_pre.png'; img.save(pre)

                import easyocr, numpy as np
                reader = easyocr.Reader(['ch_sim'], gpu=False)
                results = reader.readtext(np.array(img), detail=1)
                print(f'[Faculty-OCR] Found {len(results)} text regions')

                # ── 规则：一条竖向分界线，左边=队列（分配），右边=全部跳过 ──
                # 找所有列标题（擎护旗/队列/总负责/场控/后勤/摄影），计算分界X
                HEADER_KW = ['擎护旗', '队列', '总负责', '场控', '后勤', '摄影']

                header_x_positions = []
                for bbox, text, conf in results:
                    x1, y1 = bbox[0]; x3, y3 = bbox[2]
                    t = text.strip()
                    if any(kw in t for kw in HEADER_KW):
                        header_x_positions.append({
                            'text': t,
                            'x1': x1, 'x2': x3, 'cx': (x1 + x3) / 2
                        })

                if header_x_positions:
                    header_x_positions.sort(key=lambda h: h['x1'])

                    # 分界线 = 最右边队列标题右边界 与 其他标题最左边 的中点
                    queue_headers = [h for h in header_x_positions
                                     if any(kw in h['text'] for kw in ['擎护旗', '队列'])]
                    other_headers = [h for h in header_x_positions
                                     if not any(kw in h['text'] for kw in ['擎护旗', '队列'])]

                    if queue_headers and other_headers:
                        # 队列标题到角色标题之间有巨大空白，分界线取空白区的 70% 位置
                        # 这样队列区域的名字列（通常 2-3 列）都能被纳入
                        gap_start = queue_headers[-1]['x2']
                        gap_end = other_headers[0]['x1']
                        divide_x = gap_start + (gap_end - gap_start) * 0.70
                    elif queue_headers:
                        divide_x = queue_headers[-1]['x2'] + 250
                    else:
                        divide_x = other_headers[0]['x1'] - 250

                    print(f'[Faculty-OCR] Headers: queue={[h["text"] for h in queue_headers]}, '
                          f'other={[h["text"] for h in other_headers]}, divide={divide_x:.0f}')

                    # 收集分界线左边的所有人名（按 Y 坐标从上到下排序）
                    queue_raw = []
                    for bbox, text, conf in sorted(results, key=lambda r: r[0][0][1]):
                        x1, y1 = bbox[0]; x3, y3 = bbox[2]
                        t = text.strip()
                        if len(t) < 2: continue
                        if any(kw in t for kw in HEADER_KW): continue

                        cx = (x1 + x3) / 2
                        if cx < divide_x:
                            corrected = fuzzy_match(t, known_names)
                            if corrected not in queue_raw:
                                queue_raw.append(corrected)

                    if queue_raw:
                        ocr_parsed_text = '\n'.join(queue_raw)
                        roster_text = ocr_parsed_text if not roster_text else roster_text + '\n' + ocr_parsed_text
                    print(f'[Faculty-OCR] ALLOCATE ({len(queue_raw)}): {queue_raw}')

                os.unlink(pre)
            except Exception as e:
                import traceback
                print(f'[Faculty-OCR ERROR] {e}')
                traceback.print_exc()
            finally:
                try: os.unlink(ip)
                except: pass

    if not roster_text:
        return '请提供队列人员名单或上传照片', 400

    # 解析队列人员姓名
    queue_names = []
    for chunk in re.split(r'[、，,\n\s]+', roster_text):
        n = chunk.strip()
        if len(n) >= 2:
            queue_names.append(n)

    # 其他角色（手动输入）
    meta_people = {}
    role_labels = {1: '总负责', 2: '场控', 3: '后勤', 4: '摄影'}
    for i, label in role_labels.items():
        v = request.form.get(f'meta_{i}', '').strip()
        if v:
            names = [n.strip() for n in re.split(r'[、，,\n\s]+', v) if len(n.strip()) >= 2]
            if names:
                meta_people[label] = names

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as t:
        t.write(excel_bytes); tmp = t.name

    try:
        wb = openpyxl.load_workbook(tmp)
        all_persons = parse_equipment_sheet(wb['装备分配'])
        name_map = {p['name']: p for p in all_persons}
        pool = build_pool(wb)

        # 从库存中找到队列人员对应的装备信息
        faculty_persons = []
        missing = []
        for name in queue_names:
            p = name_map.get(name)
            if p:
                faculty_persons.append(dict(p))  # copy
            else:
                print(f'[Faculty] Unknown person: {name}')
                missing.append(name)

        # 保存初始装备状态（用于前端显示新旧对比）
        original_equip = {}
        for p in faculty_persons:
            for k in ['uniform', 'hat', 'boots', 'belt']:
                original_equip[f'{p["name"]}|{k}'] = p.get(k, '')

        # 冲突检测与解决
        conflicts = detect_faculty_conflicts(faculty_persons)
        reassigns, changed = resolve_faculty_conflicts(conflicts, faculty_persons, pool)
        b64 = generate_faculty_excel(faculty_persons, changed)

        # 按排序后的顺序返回预览数据
        sorted_persons = sort_people_by_uniform(faculty_persons)

        return jsonify(
            success=True,
            message=f'生成完成: {len(faculty_persons)} 人, {len(conflicts)} 个冲突, {len(reassigns)} 个重分配' + (f'（{len(missing)} 人未找到）' if missing else ''),
            conflicts_count=len(conflicts),
            reassignments_count=len(reassigns),
            sorted_persons=[dict(name=p['name'], gender=p['gender'],
                uniform=p.get('uniform',''), hat=p.get('hat',''),
                boots=p.get('boots',''), belt=p.get('belt','')) for p in sorted_persons],
            changes={k: v for k, v in changed.items()},
            original_equip=original_equip,
            missing=missing,
            conflicts=[dict(
                item_type={'uniform':'礼服','hat':'礼帽','boots':'马靴','belt':'腰带'}.get(c['item_type'], c['item_type']),
                item_code=c['item_code'],
                person_to_move=c['person_to_move'],
                person_to_keep=c['person_to_keep']) for c in conflicts],
            reassignments=[dict(person=r['person'],
                item_type={'uniform':'礼服','hat':'礼帽','boots':'马靴','belt':'腰带'}.get(r['item_type'], r['item_type']),
                old_item=r['old_item'], new_item=r['new_item']) for r in reassigns],
            excel_base64=b64,
            ocr_text=(ocr_parsed_text if image_file and image_file.filename else ''),
            meta_people=meta_people,
        )
    finally:
        os.unlink(tmp)


if __name__ == '__main__':
    from waitress import serve
    print(f'\n   礼服自动分配系统启动!')
    print(f'   http://localhost:{PORT}\n')
    serve(app, host='0.0.0.0', port=PORT, threads=8, channel_timeout=300)
