import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

old = '''<main>
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
</main>'''

new = '''<main>
<div class="entries">
<a href="/faculty" class="entry">
  <div class="icon">&#127891;</div>
  <h2>院系升旗礼服分配</h2>
  <p>上传礼服库存表 + 拍照上传人员安排表<br>自动识别 → 按尺寸排序 → 冲突检测 → 下载分配表</p>
</a>
</div>
</main>'''

if old in content:
    content = content.replace(old, new)
    with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'w', encoding='utf-8') as f:
        f.write(content)
    print("REPLACED successfully")
else:
    print("NOT FOUND")
    # Try to find what's different
    idx = content.find('<main>')
    if idx > 0:
        snippet = content[idx:idx+len(old)+100]
        for i, (a, b) in enumerate(zip(old, snippet)):
            if a != b:
                print(f"First diff at position {i}: old={repr(old[max(0,i-10):i+10])}, new={repr(snippet[max(0,i-10):i+10])}")
                break
