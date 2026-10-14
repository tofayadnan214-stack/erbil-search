from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import sqlite3
import urllib.parse

DB_PATH = 'erbil.db'

def clean_txt(val):
    if val is None: return ''
    return re.sub(r'[^\u0600-\u06FFa-zA-Z0-9\s\-_\/]', '', str(val)).strip()

def clean_num(val):
    if val is None or val == '': return ''
    return str(val).split('.')[0].strip()

def clean_birth(val):
    s = clean_num(val)
    return s[:4] if len(s) >= 4 else s

def norm_kurdish(text):
    if not text: return ''
    replacements = {
        'ۆ': 'و', 'ڕ': 'ر', 'ڵ': 'ل', 'پ': 'ب', 'چ': 'ج', 'ژ': 'ز',
        'گ': 'ك', 'ک': '_', 'ك': '_', 'ی': '_', 'ي': '_', 'ى': '_',
        'ێ': '_', 'ە': '_', 'ه': '_', 'ة': '_', 'أ': '_', 'إ': '_',
        'آ': '_', 'ا': '_', 'س': '_', 'ص': '_'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.strip()

HTML_PAGE = """<!DOCTYPE html>
<html lang="ku" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>سیستەمی گەڕانی داتابەیسی هەولێر</title>
<style>
  :root {
    --bg-main: #050608;
    --bg-card: #0c0e14;
    --bg-input: #040507;
    --border-gold: #4a3a14;
    --amber: #f59e0b;
    --amber-light: #fbbf24;
    --amber-dim: #b45309;
    --emerald: #10b981;
  }
  * { box-sizing: border-box; font-family: system-ui, -apple-system, Tahoma, sans-serif; }
  body { background-color: var(--bg-main); color: var(--amber); margin: 0; padding: 12px; direction: rtl; text-align: right; }
  .container { max-width: 650px; margin: 0 auto; padding-bottom: 40px; }
  .header-box { background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 12px; padding: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
  .header-title { font-size: 16px; font-weight: 900; color: var(--amber); margin: 0; }
  .header-sub { font-size: 11px; color: var(--amber-dim); margin-top: 4px; }
  .live-badge { font-size: 11px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--emerald); color: var(--emerald); font-weight: bold; }
  .panel { background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 12px; padding: 15px; margin-bottom: 14px; }
  .sec-title { font-size: 14px; font-weight: bold; color: var(--amber); margin: 0 0 12px 0; border-bottom: 1px solid #262010; padding-bottom: 8px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 10px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
  .field-lbl { display: block; font-size: 12px; color: var(--amber); margin-bottom: 5px; font-weight: bold; }
  input { width: 100%; background: var(--bg-input); color: var(--amber-light); border: 1px solid var(--border-gold); padding: 11px 10px; border-radius: 8px; font-size: 14px; font-weight: bold; outline: none; }
  input::placeholder { color: #6b4c1b; font-weight: normal; font-size: 12px; }
  input:focus { border-color: var(--amber); }
  .btn-search { width: 100%; background: var(--amber); color: #000; font-weight: 900; border: none; padding: 13px; border-radius: 8px; font-size: 15px; cursor: pointer; }
  .btn-clear { width: 100%; background: #14120d; color: var(--amber); border: 1px solid var(--border-gold); padding: 9px; border-radius: 8px; font-size: 12px; margin-top: 8px; cursor: pointer; font-weight: bold; }
  .rec-card { background: #090b10; border: 1px solid var(--border-gold); border-radius: 10px; padding: 14px; margin-top: 12px; }
  .rec-head { font-size: 17px; font-weight: 900; color: var(--amber-light); border-bottom: 1px solid #262010; padding-bottom: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; }
  .rec-row { display: flex; justify-content: space-between; padding: 6px 8px; border-bottom: 1px solid #14161f; font-size: 13px; }
  .lbl { color: var(--amber-dim); }
  .val { color: var(--amber); font-weight: bold; }
  .fam-btn { width: 100%; margin-top: 12px; background: rgba(245, 158, 11, 0.14); color: var(--amber-light); border: 1px solid var(--amber); padding: 10px; border-radius: 8px; font-weight: bold; font-size: 13px; cursor: pointer; }
</style>
</head>
<body>
<div class="container">
  <div class="header-box">
    <div>
      <h1 class="header-title">⚡ سیستەمی زانیاری و نفوسی هەولێر</h1>
      <div class="header-sub">بەستراوەتەوە بە ١,٧١٢,٩٦١ تۆماری فەرمی (erbil.db)</div>
    </div>
    <span class="live-badge">● PUBLIC LIVE</span>
  </div>

  <div class="panel">
    <div class="sec-title">🔍 گەڕان بەپێی خانەکانی ناو</div>
    <div class="grid-3">
      <div>
        <label class="field-lbl">١. ناوی یەکەم:</label>
        <input type="text" id="fFirst" placeholder="محمد..." onkeydown="if(event.key==='Enter') runSearch()" />
      </div>
      <div>
        <label class="field-lbl">٢. ناوی باوک:</label>
        <input type="text" id="fFather" placeholder="شورش..." onkeydown="if(event.key==='Enter') runSearch()" />
      </div>
      <div>
        <label class="field-lbl">٣. ناوی باپیر:</label>
        <input type="text" id="fGrand" placeholder="صدیق..." onkeydown="if(event.key==='Enter') runSearch()" />
      </div>
    </div>
    <div class="grid-2">
      <div>
        <label class="field-lbl">📅 ساڵی لەدایکبوون:</label>
        <input type="text" id="fBirth" placeholder="نموونە: 2009" onkeydown="if(event.key==='Enter') runSearch()" />
      </div>
      <div>
        <label class="field-lbl">👨‍👩‍👧‍👦 ژمارەی خێزان:</label>
        <input type="text" id="fFam" placeholder="ژمارەی فۆڕم..." onkeydown="if(event.key==='Enter') runSearch()" />
      </div>
    </div>
    <button class="btn-search" onclick="runSearch()">🔍 گەڕان لە داتابەیسدا</button>
    <button class="btn-clear" onclick="clearFields()">🧹 پاککردنەوەی خانەکان</button>
  </div>

  <div class="panel" id="resPanel" style="display:none;">
    <div class="sec-title" id="resStatus">ئەنجامەکان</div>
    <div id="resList"></div>
  </div>
</div>

<script>
function clearFields() {
  ['fFirst','fFather','fGrand','fBirth','fFam'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('fFirst').focus();
}

async function runSearch(famOverride = null) {
  const f1 = famOverride ? '' : document.getElementById('fFirst').value.trim();
  const f2 = famOverride ? '' : document.getElementById('fFather').value.trim();
  const f3 = famOverride ? '' : document.getElementById('fGrand').value.trim();
  const birth = famOverride ? '' : document.getElementById('fBirth').value.trim();
  const fam = famOverride ? String(famOverride) : document.getElementById('fFam').value.trim();

  if (!f1 && !f2 && !f3 && !birth && !fam) {
    alert("تکایە لانیکەم خانەیەک پڕ بکەرەوە!");
    return;
  }

  const panel = document.getElementById('resPanel');
  const status = document.getElementById('resStatus');
  const list = document.getElementById('resList');
  panel.style.display = 'block';
  status.innerText = "⏳ خەریکی گەڕانە...";
  list.innerHTML = "";

  const url = `/api/search?f1=${encodeURIComponent(f1)}&f2=${encodeURIComponent(f2)}&f3=${encodeURIComponent(f3)}&birth=${encodeURIComponent(birth)}&fam=${encodeURIComponent(fam)}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (data.length === 0) {
      status.innerText = "❌ هیچ زانیارییەک نەدۆزرایەوە.";
      return;
    }
    status.innerText = fam ? `👨‍👩‍👧‍👦 ئەندامانی خێزانی (${fam}) — ${data.length} کەس` : `✅ ئەنجامە دۆزراوەکان: ${data.length} کەس`;
    list.innerHTML = data.map((r, i) => `
      <div class="rec-card">
        <div class="rec-head">
          <span>👤 ${i + 1}. ${r.p_first} ${r.p_father} ${r.p_grand}</span>
          <span style="font-size:12px;">زنجیرە: ${r.seq_no || '-'}</span>
        </div>
        <div class="rec-row"><span class="lbl">🤱 ناوی دایک:</span><span class="val">${r.p_mother} ${r.gr_mother}</span></div>
        <div class="rec-row"><span class="lbl">📅 لەدایکبوون:</span><span class="val">${r.p_birth || '-'}</span></div>
        <div class="rec-row"><span class="lbl">👨‍👩‍👧‍👦 ژمارەی خێزان:</span><span class="val">${r.fam_no || '-'} (زنجیرە: ${r.seq_no || '-'})</span></div>
        <div class="rec-row"><span class="lbl">🪪 ناسنامە و تۆمار:</span><span class="val">${r.ss_id_no || '-'} | تۆمار: ${r.ss_lg_no || '-'} | لاپەڕە: ${r.ss_pg_no || '-'}</span></div>
        <div class="rec-row"><span class="lbl">🏢 بنکە و پیشە:</span><span class="val">${r.rc_no || ''} ${r.ss_br_nm || '-'} | ${r.p_job || '-'}</span></div>
        <button class="fam-btn" onclick="runSearch('${r.fam_no}')">👨‍👩‍👧‍👦 پیشاندانی هەموو ئەندامانی ئەم خێزانە (${r.fam_no})</button>
      </div>
    `).join('');
  } catch (e) {
    status.innerText = "⚠️ هەڵە لە پەیوەندی؛ دووبارە هەوڵ بدەرەوە.";
  }
}
</script>
</body>
</html>"""

class PublicServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == '/api/search':
                params = urllib.parse.parse_qs(parsed.query)
                f1 = norm_kurdish(params.get('f1', [''])[0])
                f2 = norm_kurdish(params.get('f2', [''])[0])
                f3 = norm_kurdish(params.get('f3', [''])[0])
                birth = params.get('birth', [''])[0].strip()
                fam = params.get('fam', [''])[0].strip()

                conn = sqlite3.connect(DB_PATH, timeout=15)
                cursor = conn.cursor()
                conds, vals = [], []
                if fam:
                    conds.append('(CAST(fam_no AS INTEGER) = CAST(? AS INTEGER) OR fam_no LIKE ?)')
                    vals.extend([fam, f"{fam}%"])
                else:
                    if f1: conds.append('p_first LIKE ?'); vals.append(f'%{f1}%')
                    if f2: conds.append('p_father LIKE ?'); vals.append(f'%{f2}%')
                    if f3: conds.append('p_grand LIKE ?'); vals.append(f'%{f3}%')
                    if birth: conds.append('p_birth LIKE ?'); vals.append(f'%{birth}%')

                where_sql = ' AND '.join(conds) if conds else '1=1'
                order_sql = ' ORDER BY CAST(seq_no AS INTEGER) ASC' if fam else ''
                cursor.execute(f"SELECT * FROM person WHERE {where_sql}{order_sql} LIMIT 80", tuple(vals))
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                conn.close()

                out = [{
                    'p_first': clean_txt(d.get('p_first')),
                    'p_father': clean_txt(d.get('p_father')),
                    'p_grand': clean_txt(d.get('p_grand')),
                    'p_mother': clean_txt(d.get('p_mother')),
                    'gr_mother': clean_txt(d.get('gr_mother')),
                    'p_birth': clean_birth(d.get('p_birth')),
                    'fam_no': clean_num(d.get('fam_no')),
                    'seq_no': clean_num(d.get('seq_no')),
                    'ss_id_no': clean_num(d.get('ss_id_no')),
                    'ss_lg_no': clean_txt(d.get('ss_lg_no')),
                    'ss_pg_no': clean_num(d.get('ss_pg_no')),
                    'rc_no': clean_num(d.get('rc_no')),
                    'ss_br_nm': clean_txt(d.get('ss_br_nm')),
                    'p_job': clean_txt(d.get('p_job'))
                } for d in (dict(zip(cols, r)) for r in rows)]

                payload = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)
            else:
                body = HTML_PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except Exception:
            pass

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 7860))
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(('0.0.0.0', PORT), PublicServer)
    print(f"Server running on port {PORT}")
    httpd.serve_forever()
