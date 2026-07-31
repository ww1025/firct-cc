from PIL import Image
import os
from collections import Counter

files = [
    r'C:\Users\夏瑞泽\Pictures\Screenshots\微信图片_20260622074545_287_261.jpg',
    r'C:\Users\夏瑞泽\Pictures\Screenshots\微信图片_20260622074546_288_261.jpg',
    r'C:\Users\夏瑞泽\Pictures\Screenshots\微信图片_20260622080032_293_261.jpg',
    r'C:\Users\夏瑞泽\Pictures\Screenshots\微信图片_20260622080035_297_261.jpg',
]

for i, f in enumerate(files):
    img = Image.open(f)
    w, h = img.size
    fname = os.path.basename(f)
    print(f'=== IMG {i+1}: {fname[-40:]} ===')
    print(f'Size: {w}x{h}')

    ratio = w / h
    orient = 'landscape' if ratio > 1 else 'portrait'
    print(f'Aspect: {ratio:.2f} ({orient})')

    samp_pts = [
        ('TOP', [0.02, 0.05, 0.10, 0.15]),
        ('MID-TOP', [0.20, 0.25, 0.30, 0.35]),
        ('CENTER', [0.40, 0.45, 0.50, 0.55]),
        ('MID-BOT', [0.60, 0.65, 0.70, 0.75]),
        ('BOTTOM', [0.80, 0.85, 0.90, 0.95]),
    ]

    for row_name, y_pcts in samp_pts:
        colors = []
        for yp in y_pcts:
            y = int(yp * h)
            for xp in [0.25, 0.50, 0.75]:
                x = int(xp * w)
                px = img.getpixel((x, y))
                if isinstance(px, int):
                    px = (px, px, px)
                colors.append(px)
        n = len(colors)
        avg_r = int(sum(c[0] for c in colors) / n)
        avg_g = int(sum(c[1] for c in colors) / n)
        avg_b = int(sum(c[2] for c in colors) / n)
        bright = int(0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b)
        bar = '#' * int(bright / 10) + '.' * (25 - int(bright / 10))
        print(f'  {row_name:8s} RGB({avg_r:3d},{avg_g:3d},{avg_b:3d}) B={bright:3d} [{bar}]')

    # Dominant colors via quantized histogram
    img_small = img.resize((100, int(100 * h / w)), Image.LANCZOS)
    px_list = list(img_small.getdata())
    color_counts = Counter()
    for p in px_list:
        q = (p[0] // 32 * 32, p[1] // 32 * 32, p[2] // 32 * 32)
        color_counts[q] += 1

    top5 = color_counts.most_common(5)
    print('  Top colors:')
    for color, count in top5:
        pct = count / len(px_list) * 100
        r, g, b = color
        print(f'    RGB({r:3d},{g:3d},{b:3d}) {pct:.0f}%')

    # Detect skin-like pixels in the center area
    cx, cy = w // 2, h // 2
    face_roi = img.crop((w // 4, h // 6, 3 * w // 4, h // 2))
    face_px = list(face_roi.getdata())
    skin = 0
    for p in face_px:
        if isinstance(p, int):
            continue
        r, g, b = p[0], p[1], p[2]
        # Simple skin heuristic
        if r > g > b and r > 60 and r < 230 and 5 < (r - g) < 80:
            skin += 1
    skin_pct = skin / len(face_px) * 100 if face_px else 0
    print(f'  Skin-like in face area: {skin_pct:.0f}%')

    # Overall brightness distribution
    all_bright = []
    for p in px_list:
        if isinstance(p, int):
            all_bright.append(p)
        else:
            all_bright.append(int(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]))
    dark = sum(1 for b in all_bright if b < 50) / len(all_bright) * 100
    mid = sum(1 for b in all_bright if 50 <= b < 180) / len(all_bright) * 100
    hi = sum(1 for b in all_bright if b >= 180) / len(all_bright) * 100
    print(f'  Brightness: Dark={dark:.0f}% Mid={mid:.0f}% Hi={hi:.0f}%')
    print()
