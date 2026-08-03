import re

NEW_FACULTY = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>院系升旗礼服分配</title>
<style>
:root {
  --green-900: #0f2518; --green-700: #1a3a2a; --green-500: #2d5a3f; --green-300: #5a8a6a;
  --gold-500: #c9a84c; --gold-300: #e0d0a0;
  --red: #c41e3a; --red-light: #fdf0f2;
  --paper: #f7f3ed; --paper-warm: #f0ebe3; --paper-card: #fefcf8;
  --ink: #2c1810; --ink-light: #5c4a3a; --ink-faint: #9c8a7a;
  --white: #ffffff; --gray-100: #f5f5f0; --gray-300: #d4d4cc; --gray-500: #8a8a80;
  --font-heading: 'SimSun','KaiTi','宋体','楷体','Noto Serif CJK SC','Songti SC','Microsoft YaHei',serif;
  --font-body: 'Microsoft YaHei','PingFang SC',system-ui,sans-serif;
  --font-mono: 'SimSun','Consolas','Courier New',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.8 var(--font-body);color:var(--ink);background:var(--paper);min-height:100vh;-webkit-font-smoothing:antialiased}
header{background:var(--green-900);color:var(--paper);padding:24px;text-align:center;border-bottom:3px solid var(--gold-500);position:relative}
header::before{content:'';display:block;height:3px;background:var(--red);position:absolute;top:0;left:0;right:0}
header a{color:var(--gold-300);text-decoration:none;font-size:13px;position:absolute;left:24px;top:50%;transform:translateY(-50%);letter-spacing:.05em;transition:color .15s}
header a:hover{color:var(--gold-500)}
h1{font-family:var(--font-heading);font-size:22px;font-weight:700;letter-spacing:.08em}
header p{font-size:13px;color:var(--gold-300);margin-top:4px;opacity:.7;letter-spacing:.06em}
main{max-width:860px;margin:32px auto;padding:0 24px}
.card{background:var(--paper-card);border:1px solid var(--ink-faint);padding:28px;margin-bottom:20px;position:relative}
.card::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:linear-gradient(180deg,var(--red),var(--gold-500) 60%,transparent 95%)}
.card h2{font-family:var(--font-heading);font-size:17px;display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:12px;border-bottom:2px solid var(--green-500);letter-spacing:.05em}
.badge{width:28px;height:28px;background:var(--green-700);color:var(--gold-300);font-family:var(--font-heading);font-size:14px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
label.block{display:block;font-family:var(--font-heading);font-weight:600;margin-bottom:6px;margin-top:14px;font-size:14px;color:var(--ink);letter-spacing:.04em}
label.block:first-child{margin-top:0}
textarea{width:100%;height:130px;border:1px solid var(--ink-faint);padding:12px;font:13px var(--font-mono);resize:vertical;background:var(--paper);color:var(--ink);line-height:1.8;transition:border-color .2s}
textarea:focus{outline:none;border-color:var(--green-700);box-shadow:0 0 0 2px rgba(26,58,42,.1)}
textarea::placeholder{color:var(--ink-faint);font-style:italic}
.up{border:2px solid var(--ink-faint);padding:32px;text-align:center;cursor:pointer;transition:all .2s;background:var(--paper);position:relative}
.up::before{content:'';position:absolute;top:8px;left:8px;width:14px;height:14px;border-top:1px solid var(--ink-faint);border-left:1px solid var(--ink-faint)}
.up::after{content:'';position:absolute;bottom:8px;right:8px;width:14px;height:14px;border-bottom:1px solid var(--ink-faint);border-right:1px solid var(--ink-faint)}
.up:hover{border-color:var(--green-500);background:var(--paper-card)}
.up:hover::before,.up:hover::after{border-color:var(--green-500)}
.up.sel{border-color:var(--green-500);background:#f2f7f3}
.up.sel::before,.up.sel::after{border-color:var(--green-500)}
.up input{display:none}
.up .n{font-family:var(--font-heading);font-weight:600;color:var(--green-500);margin-top:8px;display:none}
.or{display:flex;align-items:center;gap:14px;margin:16px 0}
.or hr{flex:1;border:none;border-top:1px solid var(--ink-faint)}
.or span{font-family:var(--font-heading);color:var(--ink-faint);font-size:13px;letter-spacing:.1em;position:relative;padding:0 8px}
.or span::before{content:'\25C6';font-size:6px;position:absolute;left:-2px;top:50%;transform:translateY(-50%);color:var(--ink-faint)}
.or span::after{content:'\25C6';font-size:6px;position:absolute;right:-2px;top:50%;transform:translateY(-50%);color:var(--ink-faint)}
.btn{width:100%;padding:14px;border:none;font-family:var(--font-heading);font-size:16px;font-weight:700;letter-spacing:.08em;cursor:pointer;transition:all .2s;text-transform:uppercase}
.btn-b{background:var(--green-700);color:var(--gold-300);border:1px solid var(--gold-500)}
.btn-b:hover:not(:disabled){background:var(--green-500);color:var(--gold-300)}
.btn-b:disabled{background:var(--gray-300);color:var(--gray-500);border-color:var(--gray-300);cursor:not-allowed}
.btn-g{background:var(--green-500);color:var(--gold-300);border:1px solid var(--gold-500)}
.btn-g:hover:not(:disabled){background:#24703a}
.btn-g:disabled{background:var(--gray-300);color:var(--gray-500);border-color:var(--gray-300);cursor:not-allowed}
.spin{width:22px;height:22px;border:2.5px solid rgba(200,168,76,.3);border-top-color:var(--gold-500);border-radius:50%;animation:s .7s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}
.roles{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.roles textarea{height:70px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border:1px solid var(--ink-faint);margin:16px 0}
.st{padding:20px 16px;text-align:center;border-right:1px solid var(--ink-faint);background:var(--paper-card);position:relative}
.st:last-child{border-right:none}
.st.c{border-top:3px solid var(--red)}.st.r{border-top:3px solid var(--gold-500)}.st.p{border-top:3px solid var(--green-500)}
.st b{font-family:var(--font-heading);font-size:30px;font-weight:700;display:block;line-height:1.1}
.st.c b{color:var(--red)}.st.r b{color:var(--gold-500)}.st.p b{color:var(--green-500)}
.st span{color:var(--ink-light);font-size:12px;letter-spacing:.08em;text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px;border:1px solid var(--ink-faint)}
th{background:var(--green-900);color:var(--gold-300);padding:8px 10px;text-align:center;font-family:var(--font-heading);font-weight:600;font-size:12px;letter-spacing:.05em;text-transform:uppercase;border:1px solid rgba(224,208,160,.15)}
td{padding:8px 10px;border:1px solid var(--ink-faint);text-align:center}
tr:nth-child(even) td{background:var(--paper-warm)}
.old{text-decoration:line-through;color:var(--ink-faint);font-size:12px}
.hl{background:#fffde7;font-weight:600}
.hint{display:none;background:#fdf8ed;border-left:3px solid var(--gold-500);padding:10px 14px;margin-top:10px;font-size:13px;color:#6b5a20}
.err{display:none;background:var(--red-light);border-left:3px solid var(--red);padding:12px 14px;color:var(--red);margin-top:12px;font-size:13px}
#load{text-align:center;padding:40px;display:none}
#load p{color:var(--ink-light);margin-top:12px;font-size:13px}
footer{text-align:center;padding:28px;font-family:var(--font-heading);font-size:12px;color:var(--ink-faint);letter-spacing:.08em}
#pt h3,#rt h3{font-family:var(--font-heading);font-size:15px;font-weight:700;margin:16px 0 6px;color:var(--ink);letter-spacing:.05em}
</style>
</head>
<body>
<header>
<a href="/">&#8592; 返回首页</a>
<h1>&#127891; 院系升旗礼服分配</h1>
<p>上传库存表 → 拍照识别人名 → 生成分配表</p>
</header>
<main>

<div class="card">
<h2><span class="badge">1</span> 上传礼服库存表 (.xlsx)</h2>
<div class="up" id="ea"><div style="font-size:36px;margin-bottom:8px">&#128206;</div><div>上传包含所有人员装备信息的Excel</div><div style="color:var(--ink-faint);font-size:13px">系统将从中提取装备库存</div>
<input type="file" id="ei" accept=".xlsx"/><div class="n" id="en"></div></div>
</div>

<div class="card">
<h2><span class="badge">2</span> 拍照上传人员安排表</h2>
<div class="up" id="ia"><div style="font-size:36px;margin-bottom:8px">&#128247;</div><div>点击上传人员安排表照片（手写也可以）</div><div style="color:var(--ink-faint);font-size:13px">AI自动识别队列人员姓名</div>
<input type="file" id="ii" accept="image/*"/><div class="n" id="inm"></div></div>
<div class="hint" id="ohint">&#9888; OCR识别结果已填入下方，请核对修正后再点生成</div>
<div class="or"><hr><span>或手动输入 / 修正队列人员</span><hr></div>
<p style="color:var(--ink-light);font-size:13px;margin-bottom:8px">每行一人或顿号分隔。总负责、场控、后勤、摄影不参与分配。</p>
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
<div id="load"><div class="spin" style="display:inline-block;border-color:rgba(200,168,76,.2);border-top-color:var(--gold-500);width:36px;height:36px"></div><p>正在识别并生成分配方案...</p></div>

<div id="res" style="display:none"><div class="card">
<h2><span class="badge">3</span> 生成结果</h2>
<p style="color:var(--ink-light);margin-bottom:16px" id="rm"></p>
<div class="stats" id="sr" style="display:none">
<div class="st c"><b id="cc">0</b><span>冲突数</span></div>
<div class="st r"><b id="rc">0</b><span>重分配</span></div>
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
  if(d.ocr_text){
    document.getElementById('rp').value=d.ocr_text;
    document.getElementById('ohint').style.display='block';
  }
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
  var h='<h3>排序后人员列表</h3><table><tr><th>序号</th><th>姓名</th><th>性别</th><th>礼服</th><th>礼帽</th><th>马靴</th><th>腰带</th></tr>';
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
  if(d.conflicts.length){
    h='<h3>冲突详情</h3><table><tr><th>装备类型</th><th>编号</th><th>需变动</th><th>保留</th></tr>';
    d.conflicts.forEach(function(c){h+='<tr><td>'+c.item_type+'</td><td>'+c.item_code+'</td><td>'+c.person_to_move+'</td><td>'+c.person_to_keep+'</td></tr>'});
    h+='</table>';
  }
  if(d.reassignments.length){
    h='<h3>重分配方案</h3><table><tr><th>姓名</th><th>装备</th><th>旧编号</th><th>新编号</th></tr>';
    d.reassignments.forEach(function(r){h+='<tr><td>'+r.person+'</td><td>'+r.item_type+'</td><td class=old>'+r.old_item+'</td><td class=hl>'+r.new_item+'</td></tr>'});
    h+='</table>';
  }
  document.getElementById('rt').innerHTML=h;
  document.getElementById('res').scrollIntoView({behavior:'smooth'});
}
</script>
</body></html>"""

import re

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'r', encoding='utf-8') as f:
    content = f.read()

idx_fac_start = content.find("FACULTY_HTML = r'''")
search_start = idx_fac_start + len("FACULTY_HTML = r'''")
idx_fac_end = content.find("</body></html>'''", search_start)

if idx_fac_end > 0:
    idx_fac_end += len("</body></html>'''")
    next_nl = content.find('\n', idx_fac_end)
    if 0 < next_nl < idx_fac_end + 20:
        idx_fac_end = next_nl + 1

old_fac = content[idx_fac_start:idx_fac_end]
new_fac = f"FACULTY_HTML = r'''{NEW_FACULTY}'''"
content = content.replace(old_fac, new_fac)
print("FACULTY_HTML replaced successfully")

with open(r"C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\server.py", 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
