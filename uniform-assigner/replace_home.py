import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

# ============ NEW HOME_HTML ============
NEW_HOME = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>礼服自动分配系统</title>
<style>
:root {
  --green-900: #0f2518; --green-700: #1a3a2a; --green-500: #2d5a3f;
  --gold-500: #c9a84c; --gold-300: #e0d0a0;
  --red: #c41e3a; --red-light: #fdf0f2;
  --paper: #f7f3ed; --paper-warm: #f0ebe3; --paper-card: #fefcf8;
  --ink: #2c1810; --ink-light: #5c4a3a; --ink-faint: #9c8a7a;
  --white: #ffffff; --gray-100: #f5f5f0; --gray-300: #d4d4cc;
  --font-heading: 'SimSun','宋体','Noto Serif CJK SC','Songti SC','Microsoft YaHei',serif;
  --font-body: 'Microsoft YaHei','PingFang SC',system-ui,sans-serif;
  --font-mono: 'SimSun','Consolas','Courier New',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.8 var(--font-body);color:var(--ink);background:var(--paper);min-height:100vh;-webkit-font-smoothing:antialiased}
/* === HEADER === */
header{background:var(--green-900);color:var(--paper);padding:36px 24px 28px;text-align:center;border-bottom:3px solid var(--gold-500);position:relative}
header::before{content:'';display:block;height:3px;background:var(--red);position:absolute;top:0;left:0;right:0}
header h1{font-family:var(--font-heading);font-size:24px;font-weight:700;letter-spacing:.1em;color:var(--gold-300)}
header p{font-size:13px;color:var(--gold-300);letter-spacing:.12em;margin-top:6px;opacity:.75}
/* === MAIN === */
main{max-width:720px;margin:48px auto;padding:0 24px}
/* === ENTRY CARD === */
.entries{display:grid;place-items:center}
.entry{display:block;background:var(--paper-card);border:1px solid var(--ink-faint);padding:48px 40px;text-align:center;text-decoration:none;color:inherit;cursor:pointer;transition:all .25s;position:relative;max-width:480px;width:100%}
.entry::after{content:'';position:absolute;inset:4px;border:1px solid var(--ink-faint);opacity:.3;pointer-events:none}
.entry:hover{border-color:var(--red);transform:translateY(-3px);box-shadow:0 12px 32px rgba(44,24,16,.12)}
.entry:hover::after{border-color:var(--red);opacity:.5}
.entry .icon{font-size:48px;margin-bottom:16px;display:block}
.entry h2{font-family:var(--font-heading);font-size:20px;font-weight:700;color:var(--ink);margin-bottom:12px;letter-spacing:.06em}
.entry p{font-size:13px;color:var(--ink-light);line-height:1.8}
/* === ORNAMENT === */
.entry::before{content:'';display:block;width:40px;height:3px;background:var(--green-500);margin:0 auto 20px;transition:width .25s}
.entry:hover::before{width:60px;background:var(--red)}
/* === FOOTER === */
footer{text-align:center;padding:32px;font-family:var(--font-heading);font-size:12px;color:var(--ink-faint);letter-spacing:.08em;border-top:1px solid var(--gray-300);margin-top:48px}
</style>
</head>
<body>
<header>
<h1>浙江大学国旗仪仗队 · 礼服自动分配系统</h1>
<p>院系升旗礼服分配</p>
</header>
<main>
<div class="entries">
<a href="/faculty" class="entry">
  <div class="icon">&#127891;</div>
  <h2>院系升旗礼服分配</h2>
  <p>上传礼服库存表 + 拍照上传人员安排表<br>自动识别 → 按尺寸排序 → 冲突检测 → 下载分配表</p>
</a>
</div>
</main>
<footer>浙江大学国旗仪仗队 &copy; 2026</footer>
</body></html>"""

# Find HOME_HTML start and end
idx_home_start = content.find("HOME_HTML = r'''")
idx_home_end_str = "</body></html>'''"
idx_home_end = content.find(idx_home_end_str, idx_home_start)
if idx_home_end > 0:
    idx_home_end += len(idx_home_end_str)
    # Find the newline after HOME_HTML closing
    next_line = content.find('\n', idx_home_end)
    if next_line > 0 and next_line < idx_home_end + 10:
        idx_home_end = next_line + 1

    old_home = content[idx_home_start:idx_home_end]
    new_home = f"HOME_HTML = r'''{NEW_HOME}'''"
    content = content.replace(old_home, new_home)
    print("HOME_HTML replaced successfully")
else:
    print("ERROR: Could not find HOME_HTML end")

# Now handle FACULTY_HTML
idx_fac_start = content.find("FACULTY_HTML = r'''")
idx_fac_end_str = "</body></html>'''"
# Find the second occurrence (after HOME_HTML)
idx_fac_end = content.find(idx_fac_end_str, idx_fac_start + 100)
if idx_fac_end > 0:
    idx_fac_end += len(idx_fac_end_str)
    next_line = content.find('\n', idx_fac_end)
    if next_line > 0 and next_line < idx_fac_end + 10:
        idx_fac_end = next_line + 1

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'w', encoding='utf-8') as f:
    f.write(content)

print("HOME_HTML written. Ready for FACULTY_HTML replacement.")
