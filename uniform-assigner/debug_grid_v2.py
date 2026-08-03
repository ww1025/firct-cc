"""离线测试排班表 OCR — 诊断为什么周五缺失、周一过多"""
import cv2, numpy as np, easyocr, re, sys
from PIL import Image
from difflib import SequenceMatcher

sys.path.insert(0, r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner')

image_path = r'c:\Users\夏瑞泽\xwechat_files\wxid_vnl456wm0r9h12_0c22\temp\RWTemp\2026-07\9e20f478899dc29eb19741386f9343c8\cfd5ca841af9d1bf15e098f16c5f3147.png'
img = Image.open(image_path).convert('RGB')
w, h = img.size
print(f'Image: {w}x{h}')

TARGET_W = min(w, 2000)
scale = TARGET_W / w
new_w, new_h = TARGET_W, int(h * scale)
img = img.resize((new_w, new_h), Image.LANCZOS)

reader = easyocr.Reader(['ch_sim'], gpu=False)
img_np = np.array(img)
gray = np.mean(img_np, axis=2).astype(np.uint8)
h_px, w_px = gray.shape

# ===== 网格检测（新参数）=====
inv = 255 - gray
binary = cv2.adaptiveThreshold(inv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

# 水平线
h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w_px // 8, 20), 1))
h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
h_proj = np.sum(h_lines, axis=1) / 255
row_ys = [i for i in range(len(h_proj)) if h_proj[i] > max(w_px * 0.03, 5)]
print(f'\nH-lines detected: {len(row_ys)} pixels')
row_seps = []
if row_ys:
    cur = [row_ys[0]]
    for y in row_ys[1:]:
        if y - cur[-1] <= 5: cur.append(y)
        else: row_seps.append(int(np.mean(cur))); cur = [y]
    row_seps.append(int(np.mean(cur)))
row_bounds = [0] + row_seps + [h_px]
print(f'Row bounds: {len(row_bounds)-1} rows at {row_seps}')

# 竖直线
v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h_px // 8, 20)))
v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
v_proj = np.sum(v_lines, axis=0) / 255
col_xs = [i for i in range(len(v_proj)) if v_proj[i] > max(h_px * 0.03, 5)]
print(f'V-lines detected: {len(col_xs)} pixels')
col_seps = []
if col_xs:
    cur = [col_xs[0]]
    for x in col_xs[1:]:
        if x - cur[-1] <= 5: cur.append(x)
        else: col_seps.append(int(np.mean(cur))); cur = [x]
    col_seps.append(int(np.mean(cur)))
col_bounds = [0] + col_seps + [w_px]
print(f'Col bounds: {len(col_bounds)-1} cols at {col_seps}')

# 过滤窄列
filtered_bounds = [col_bounds[0]]
for i in range(1, len(col_bounds) - 1):
    if col_bounds[i] - filtered_bounds[-1] >= 10:
        filtered_bounds.append(col_bounds[i])
filtered_bounds.append(col_bounds[-1])
col_bounds = filtered_bounds
print(f'After filtering: {len(col_bounds)-1} cols')

# ===== 直接做 X 坐标聚类（不看网格线）=====
print('\n--- Direct X-clustering of all OCR blocks ---')
results = reader.readtext(img_np, detail=1, low_text=0.2, text_threshold=0.3)

# Filter edges
filtered = []
for bbox, text, conf in results:
    x1, y1 = bbox[0]; x3, y3 = bbox[2]
    t = text.strip()
    if not t: continue
    if x1 <= 5 and y1 <= 5: continue
    if x3 >= new_w - 5 and y3 >= new_h - 5: continue
    filtered.append((bbox, t, conf))

results = filtered

# Sort by x center, find column gaps
blocks = []
for bbox, text, conf in results:
    x1, y1 = bbox[0]; x3, y3 = bbox[2]
    blocks.append({'text': text, 'x1': x1, 'x3': x3, 'cx': (x1+x3)/2, 'y1': y1})

blocks.sort(key=lambda b: b['cx'])

# Cluster by X gaps
if blocks:
    clusters = [[blocks[0]]]
    for b in blocks[1:]:
        if b['cx'] - clusters[-1][-1]['cx'] < 30:  # Narrower gap threshold
            clusters[-1].append(b)
        else:
            clusters.append([b])
    print(f'X-clusters found: {len(clusters)}')
    for i, cl in enumerate(clusters):
        xs = [b['x1'] for b in cl]
        texts = [b['text'] for b in cl]
        print(f'  Cluster {i}: x={min(xs):.0f}-{max(xs):.0f}, count={len(cl)}, texts={texts[:5]}')

# ===== Day label detection in full image =====
print('\n--- Day label search ---')
DAY_LABELS = ['周一', '周二', '周三', '周四', '周五']
for bbox, text, conf in results:
    for dl in DAY_LABELS:
        if dl in text or any(c in text for c in dl):
            x1, y1 = bbox[0]
            print(f'  Found "{text}" at x={x1:.0f},y={y1:.0f} (conf={conf:.2f})')
