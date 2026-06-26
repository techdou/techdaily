import sys
import os
import re
import subprocess
from datetime import datetime

WEBROOT = "/var/www/news.techdou.com"

# Find entries (use sudo since files may be owned by www-data)
result = subprocess.run(['sudo', 'find', WEBROOT + '/20', '-name', 'index.html', '-path', '*/??/??/*'],
                       capture_output=True, text=True)
entries = [f for f in result.stdout.strip().split('\n') if f.strip()]
entries.sort(reverse=True)

items = []
for full_path in entries:
    if not os.path.exists(full_path):
        # Try sudo cat
        try:
            content = subprocess.check_output(['sudo', 'cat', full_path], stderr=subprocess.DEVNULL).decode('utf-8')
        except:
            continue
    else:
        with open(full_path) as fp:
            content = fp.read()
    
    dir_path = os.path.dirname(full_path)
    m = re.search(r'(\d{4}/\d{2}/\d{2})', dir_path)
    if not m:
        continue
    date_path = m.group(1)
    y, mo, d = date_path.split('/')
    
    title_match = re.search(r'<title>([^<]+)</title>', content)
    title = title_match.group(1) if title_match else f"TechDaily {date_path}"
    title = re.sub(r'^TechDaily\s*[·•\-]\s*', '', title)
    title = re.sub(r'^TechDaily$', '', title)
    title = title.strip() or f"{y}年{mo}月{d}日"
    
    try:
        dt = datetime(int(y), int(mo), int(d))
        weekday_cn = ['星期一','星期二','星期三','星期四','星期五','星期六','星期日'][dt.weekday()]
    except:
        weekday_cn = "星期?"
    
    has_audio = os.path.exists(f"{dir_path}/audio.mp3")
    if not has_audio:
        # Check with sudo
        r = subprocess.run(['sudo', 'test', '-f', f"{dir_path}/audio.mp3"], capture_output=True)
        has_audio = (r.returncode == 0)
    
    story_count = len(re.findall(r'<article class="story"', content))
    cats = re.findall(r'class="cat-pill"[^>]*>([^<]+)<', content)
    cats = list(dict.fromkeys(cats))[:3]
    
    items.append({
        'date_path': date_path,
        'y': y, 'mo': mo, 'd': d,
        'date_compact': f"{mo}.{d}",
        'date_long': f"{y}年{mo}月{d}日",
        'weekday': weekday_cn,
        'title': title,
        'has_audio': has_audio,
        'story_count': story_count,
        'categories': cats,
    })

groups = {}
for it in items:
    ym = f"{it['y']}/{it['mo']}"
    groups.setdefault(ym, []).append(it)

OUT_PATH = "/var/www/news.techdou.com/.build/archive-gen.html"
    out = open(OUT_PATH, 'a')
    for ym, group_items in groups.items():
        out.write(f'  <div class="archive-month-group" data-month="{ym}">\n')
        out.write(f'    <div class="archive-month-title"><span class="num">{ym.replace("/", " · ")}</span><span class="count">{len(group_items)} 期</span></div>\n')
        out.write(f'    <div class="archive-grid">\n')
        for it in group_items:
            tags_html = ''
            for c in it['categories']:
                c_esc = c.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                tags_html += f'<span class="archive-tag">{c_esc}</span>'
            if it['has_audio']:
                tags_html += '<span class="archive-tag audio">🎙 音频</span>'
            
            t_esc = it['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            out.write(f'''      <a class="archive-item" data-date="{it['y']}-{it['mo']}-{it['d']}" data-audio="{1 if it['has_audio'] else 0}" href="/{it['date_path']}/">
        <div class="archive-item-head">
          <div class="archive-date">{it['date_compact']}</div>
          <div class="archive-weekday">{it['weekday']}</div>
        </div>
        <div class="archive-title-text">{t_esc}</div>
        <div class="archive-tags">{tags_html}</div>
        <div class="archive-meta">
          <span>{it['date_long']}</span>
          <span class="archive-count">{it['story_count']} 篇 <span class="archive-arrow">→</span></span>
        </div>
      </a>
''')
        out.write('    </div>\n')
        out.write('  </div>\n')
    out.close()

print(f"Processed {len(items)} items in {len(groups)} month groups", file=sys.stderr)
