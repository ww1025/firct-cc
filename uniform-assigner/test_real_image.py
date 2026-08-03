import requests, json, sys

# Use the real schedule image and Excel
image_path = r'c:\Users\夏瑞泽\xwechat_files\wxid_vnl456wm0r9h12_0c22\temp\RWTemp\2026-07\9e20f478899dc29eb19741386f9343c8\cfd5ca841af9d1bf15e098f16c5f3147.png'
excel_path = r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\本月礼服分配.xlsx'

print(f'Image exists: {__import__("os").path.exists(image_path)}')
print(f'Excel exists: {__import__("os").path.exists(excel_path)}')

with open(image_path, 'rb') as fi, open(excel_path, 'rb') as fe:
    files = {
        'excel': ('schedule.xlsx', fe, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        'image': ('schedule.png', fi, 'image/png')
    }
    r = requests.post('http://localhost:8765/generate', files=files)

print(f'Status: {r.status_code}')
if r.status_code == 200:
    j = r.json()
    print(f"Message: {j['message']}")
    print(f"Conflicts: {j['conflicts_count']}, Reassignments: {j['reassignments_count']}")
    if j.get('ocr_text'):
        print(f"\nOCR output ({len(j['ocr_text'].splitlines())} lines):")
        print(j['ocr_text'])
    else:
        print("\nNo OCR text returned!")
else:
    print(r.text[:500])
