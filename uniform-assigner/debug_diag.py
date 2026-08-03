"""诊断为什么 column-level re-OCR 返回空"""
import cv2, numpy as np, easyocr, sys
from PIL import Image

image_path = r'c:\Users\夏瑞泽\xwechat_files\wxid_vnl456wm0r9h12_0c22\temp\RWTemp\2026-07\9e20f478899dc29eb19741386f9343c8\cfd5ca841af9d1bf15e098f16c5f3147.png'
img = Image.open(image_path).convert('RGB')
w, h = img.size

TARGET_W = min(w, 2000)
scale = TARGET_W / w
new_w, new_h = TARGET_W, int(h * scale)
img = img.resize((new_w, new_h), Image.LANCZOS)

reader = easyocr.Reader(['ch_sim'], gpu=False)
img_np = np.array(img)
gray = np.mean(img_np, axis=2).astype(np.uint8)

results = reader.readtext(img_np, detail=1, low_text=0.2, text_threshold=0.3)

filtered = []
for bbox, text, conf in results:
    x1, y1 = bbox[0]; x3, y3 = bbox[2]
    t = text.strip()
    if not t: continue
    if x1 <= 5 and y1 <= 5: continue
    if x3 >= new_w - 5 and y3 >= new_h - 5: continue
    filtered.append((bbox, t, conf))

blocks = []
for bbox, text, conf in filtered:
    x1, y1 = bbox[0]; x3, y3 = bbox[2]
    blocks.append({'text': text, 'x1': x1, 'x3': x3, 'cx': (x1+x3)/2, 'y1': y1, 'y3': y3})

blocks.sort(key=lambda b: b['cx'])
x_clusters = [[blocks[0]]]
for b in blocks[1:]:
    if b['cx'] - x_clusters[-1][-1]['cx'] < 40:
        x_clusters[-1].append(b)
    else:
        x_clusters.append([b])

print(f'Clusters: {len(x_clusters)}')

# Analyze each column
for ci, cluster in enumerate(x_clusters):
    cluster.sort(key=lambda b: b['y1'])
    col_x1 = max(0, int(min(b['x1'] for b in cluster)) - 5)
    col_x2 = min(new_w, int(max(b['x3'] for b in cluster)) + 5)
    col_y1 = max(0, int(min(b['y1'] for b in cluster)) - 5)
    col_y2 = min(new_h, int(max(b['y3'] for b in cluster)) + 5)

    col_w = col_x2 - col_x1
    col_h = col_y2 - col_y1
    col_img = gray[col_y1:col_y2, col_x1:col_x2]

    scale_col = max(1.0, 600.0 / col_img.shape[0])
    col_big = cv2.resize(col_img,
        (int(col_img.shape[1] * scale_col), int(col_img.shape[0] * scale_col)),
        interpolation=cv2.INTER_LANCZOS4)

    print(f'\nC{ci}: crop={col_w}x{col_h}, scaled={col_big.shape[1]}x{col_big.shape[0]}')

    # Try different OCR params
    for lt in [0.05, 0.1, 0.2]:
        for tt in [0.1, 0.2, 0.3]:
            res = reader.readtext(col_big, detail=1, low_text=lt, text_threshold=tt)
            # Only count meaningful results
            good = [(t, c) for _, t, c in res if len(t.strip()) >= 2]
            if good:
                print(f'  lt={lt}, tt={tt}: {len(good)} results: {good[:5]}')
