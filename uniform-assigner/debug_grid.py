"""离线测试：直接对排班表图片做网格检测 + OCR，验证每列分配"""
import cv2, numpy as np
import easyocr
from PIL import Image

image_path = r'c:\Users\夏瑞泽\xwechat_files\wxid_vnl456wm0r9h12_0c22\temp\RWTemp\2026-07\9e20f478899dc29eb19741386f9343c8\cfd5ca841af9d1bf15e098f16c5f3147.png'

img = Image.open(image_path).convert('RGB')
w, h = img.size
print(f'Image size: {w}x{h}')

TARGET_W = min(w, 2000)
scale = TARGET_W / w
new_w, new_h = TARGET_W, int(h * scale)
img = img.resize((new_w, new_h), Image.LANCZOS)
print(f'Resized: {new_w}x{new_h}')

reader = easyocr.Reader(['ch_sim'], gpu=False)

# ===== Grid detection =====
img_np = np.array(img)
gray = np.mean(img_np, axis=2).astype(np.uint8)
h_px, w_px = gray.shape
inv = 255 - gray

# Try both OTSU and adaptive
_, binary_otsu = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
binary_adapt = cv2.adaptiveThreshold(inv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

# Horizontal lines with smaller kernel
for kernel_div in [3, 5, 8, 10]:
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w_px // kernel_div, 20), 1))
    h_lines = cv2.morphologyEx(binary_adapt, cv2.MORPH_OPEN, h_kernel)
    h_proj = np.sum(h_lines, axis=1) / 255
    for threshold_ratio in [0.03, 0.05, 0.1]:
        thresh = max(w_px * threshold_ratio, 5)
        row_ys = [i for i in range(len(h_proj)) if h_proj[i] > thresh]
        print(f'H-kernel 1/{kernel_div}, thresh={threshold_ratio:.0%} ({thresh:.0f}px): {len(row_ys)} line pixels detected')

# Vertical lines with smaller kernel
for kernel_div in [3, 5, 8, 10]:
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h_px // kernel_div, 20)))
    v_lines = cv2.morphologyEx(binary_adapt, cv2.MORPH_OPEN, v_kernel)
    v_proj = np.sum(v_lines, axis=0) / 255
    for threshold_ratio in [0.03, 0.05, 0.1]:
        thresh = max(h_px * threshold_ratio, 5)
        col_xs = [i for i in range(len(v_proj)) if v_proj[i] > thresh]
        print(f'V-kernel 1/{kernel_div}, thresh={threshold_ratio:.0%} ({thresh:.0f}px): {len(col_xs)} line pixels detected')

# ===== Full-image OCR fallback (current behavior) =====
print('\n--- Full-image OCR ---')
results = reader.readtext(img_np, detail=1, low_text=0.2, text_threshold=0.3)
DAY_LABELS = ['周一', '周二', '周三', '周四', '周五']
for bbox, text, conf in results:
    x1, y1 = bbox[0]; x3, y3 = bbox[2]
    t = text.strip()
    if any(d in t for d in DAY_LABELS) or len(t) >= 2:
        print(f'  [{x1:.0f},{y1:.0f}-{x3:.0f},{y3:.0f}] ({conf:.2f}) "{t}"')
