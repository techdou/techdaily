#!/bin/bash
# gen-archive.sh — Regenerate archive.html for TechDaily
# Scans the server's deployed daily pages and generates a clean archive.html
# Usage: bash scripts/gen-archive.sh
set -e

REMOTE="ubuntu@43.153.24.30"
WEBROOT="/var/www/news.techdou.com"

ssh "$REMOTE" "python3 - > /tmp/archive-gen.html" << 'PYEOF'
import os, datetime, sys
from collections import OrderedDict

WEBROOT = "/var/www/news.techdou.com"
entries = []
for root, dirs, files in os.walk(WEBROOT):
    for fn in files:
        if fn == "index.html":
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, WEBROOT).replace("\\", "/")
            parts = rel.split("/")
            if len(parts) >= 4 and parts[0].startswith("20"):
                entries.append(rel)

entries.sort(reverse=True)

items = []
for rel in entries:
    parts = rel.split("/")
    y, m, d = parts[-4], parts[-3], parts[-2]
    try:
        date_obj = datetime.date(int(y), int(m), int(d))
    except ValueError:
        continue
    weekday_zh = ['星期一','星期二','星期三','星期四','星期五','星期六','星期日'][date_obj.weekday()]
    date_iso = f"{y}-{m}-{d}"
    date_short = f"{m}.{d}"
    url = f"/{y}/{m}/{d}/"
    items.append({"date_iso": date_iso, "date_short": date_short, "weekday": weekday_zh, "url": url, "ym": f"{y}/{m}"})

html = []
html.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>往期回顾 · TechDaily</title>
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Noto+Serif+SC:wght@400;600;700;900&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a1a1a;--ink-soft:#2b251f;--ink-muted:#6b6358;--paper:#f5f1e8;--paper-warm:#efe9dc;--paper-card:#fffdf8;--paper-dark:#e0d8c8;--accent:#8b1a1a;--accent-soft:#c44d4d;--accent-bg:rgba(139,26,26,0.06);--rule:#c8c0b0;--rule-soft:#ddd6c8;--font-serif:'Noto Serif SC','Playfair Display',Georgia,serif;--font-display:'Playfair Display','Noto Serif SC',Georgia,serif;--font-sans:'DM Sans',-apple-system,'PingFang SC',sans-serif;--font-mono:'JetBrains Mono','SF Mono',Consolas,monospace;--shadow-sm:0 1px 3px rgba(0,0,0,0.04);--shadow-md:0 4px 16px rgba(0,0,0,0.08)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{font-family:var(--font-sans);background:var(--paper);color:var(--ink);line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.header{background:var(--ink);color:var(--paper);padding:48px 20px 36px;text-align:center;position:relative;overflow:hidden}
.header::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;background:radial-gradient(ellipse at top,rgba(196,77,77,0.15) 0%,transparent 60%);pointer-events:none}
.header-inner{position:relative;max-width:1200px;margin:0 auto}
.header h1{font-family:var(--font-display);font-size:clamp(2rem,5vw,3.2rem);font-weight:900;letter-spacing:-0.02em;line-height:1;margin-bottom:10px}
.header h1 .accent{color:var(--accent-soft);font-style:italic}
.header .sub{font-family:var(--font-serif);font-size:clamp(.9rem,1.5vw,1.05rem);font-style:italic;opacity:.7}
.header .logo{width:48px;height:48px;border-radius:10px;margin:0 auto 16px;display:block}
.nav{max-width:1200px;margin:0 auto;padding:18px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--rule-soft)}
.back{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;font-family:var(--font-sans);font-size:.85rem;color:var(--ink);border:1px solid var(--rule);border-radius:6px;background:var(--paper-card);transition:all .2s}
.back:hover{background:var(--accent);color:var(--paper-card);border-color:var(--accent)}
.filter{display:flex;gap:6px;flex-wrap:wrap}
.filter-btn{font-family:var(--font-mono);font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-muted);background:transparent;padding:5px 12px;border-radius:20px;cursor:pointer;transition:all .15s;border:1px solid transparent}
.filter-btn:hover{color:var(--accent);background:var(--accent-bg)}
.filter-btn.active{color:#fff;background:var(--accent);border-color:var(--accent)}
.container{max-width:1200px;margin:0 auto;padding:32px 20px 60px}
.month-group{margin-bottom:36px}
.month-title{font-family:var(--font-display);font-size:1.4rem;font-weight:700;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid var(--ink);display:flex;align-items:baseline;gap:10px}
.month-title .num{color:var(--accent);font-style:italic}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.item{background:var(--paper-card);border:1px solid var(--rule-soft);border-radius:10px;padding:18px;cursor:pointer;transition:all .25s;display:flex;flex-direction:column;gap:10px;position:relative;overflow:hidden}
.item::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--accent);transform:scaleY(0);transform-origin:top;transition:transform .3s}
.item:hover{box-shadow:var(--shadow-md);transform:translateY(-2px);border-color:var(--accent-soft)}
.item:hover::before{transform:scaleY(1)}
.item-head{display:flex;align-items:baseline;gap:8px;justify-content:space-between}
.item-date{font-family:var(--font-display);font-size:1.5rem;font-weight:900;color:var(--accent);line-height:1;letter-spacing:-0.02em}
.item-weekday{font-family:var(--font-mono);font-size:.7rem;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em}
.item-arrow{opacity:.4;transition:all .2s;font-size:.85rem;align-self:center}
.item:hover .item-arrow{opacity:1;transform:translateX(3px);color:var(--accent)}
.footer{max-width:1200px;margin:0 auto;padding:24px 20px 40px;text-align:center;border-top:1px solid var(--rule-soft)}
.footer-text{font-family:var(--font-mono);font-size:.72rem;color:var(--ink-muted);letter-spacing:.05em}
.footer-text .accent{color:var(--accent);font-weight:600}
@media(max-width:768px){.header{padding:36px 16px 28px}.nav{padding:14px 16px;flex-direction:column;align-items:stretch;gap:12px}.container{padding:24px 16px 40px}.grid{grid-template-columns:1fr;gap:10px}.item{padding:14px}.item-date{font-size:1.3rem}}
@media(prefers-reduced-motion:reduce){.item{transition:none}.item:hover{transform:none}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<img src="/assets/favicon.svg" class="logo" alt="TechDaily" onerror="this.style.display='none'">
<h1>往期<span class="accent">回顾</span></h1>
<div class="sub">— TechDaily 科技日报归档</div>
</div></header>
<nav class="nav"><a href="/" class="back">← 返回今日日报</a><div class="filter"><button class="filter-btn active" data-filter="recent">最近 7 天</button><button class="filter-btn" data-filter="all">全部</button></div></nav>
<main class="container" id="container">''')

months = OrderedDict()
for it in items:
    if it["ym"] not in months:
        months[it["ym"]] = []
    months[it["ym"]].append(it)

for ym, month_items in months.items():
    y, m = ym.split('/')
    html.append(f'<div class="month-group" data-month="{ym}"><div class="month-title"><span class="num">{y} · {m}</span></div><div class="grid">')
    for it in month_items:
        html.append(f'<a class="item" data-date="{it["date_iso"]}" href="{it["url"]}"><div class="item-head"><div class="item-date">{it["date_short"]}</div><div class="item-weekday">{it["weekday"]}</div></div><span class="item-arrow">→</span></a>')
    html.append('</div></div>')

html.append('''</main>
<footer class="footer"><div class="footer-text">© 2026 <span class="accent">TechDaily</span> · techdou.com</div></footer>
<iframe src="/pet.html?v=5" class="pet-iframe" id="petIframe" title="DouknowAI Pet" style="position:fixed;top:0;left:0;width:100vw;height:100vh;border:none;pointer-events:none;z-index:50;background:transparent;overflow:hidden"></iframe>
<script>
const filterBtns=document.querySelectorAll('.filter-btn');const allItems=document.querySelectorAll('.item');
function applyFilter(f){const n=new Date();const w=new Date(n.getTime()-7*24*60*60*1000);allItems.forEach(i=>{let s=true;if(f==='recent'){const d=new Date(i.dataset.date);s=d>=w}i.style.display=s?'':'none'});document.querySelectorAll('.month-group').forEach(g=>{const v=g.querySelectorAll('.item:not([style*="display: none"])');g.style.display=v.length===0?'none':''})}
filterBtns.forEach(b=>b.addEventListener('click',()=>{filterBtns.forEach(x=>x.classList.remove('active'));b.classList.add('active');applyFilter(b.dataset.filter)}));
applyFilter('recent');
const obs=new IntersectionObserver(e=>{e.forEach(x=>{if(x.isIntersecting)x.target.classList.add('visible')})},{threshold:0.06});
allItems.forEach((el,i)=>{el.style.opacity='0';el.style.transform='translateY(14px)';el.style.transition='opacity .4s ease, transform .4s ease';el.style.transitionDelay=(i*30)+'ms';obs.observe(el)});
const visObs=new MutationObserver(m=>{m.forEach(x=>{if(x.target.classList.contains('visible')){x.target.style.opacity='1';x.target.style.transform='translateY(0)'}})});
allItems.forEach(el=>visObs.observe(el,{attributes:true,attributeFilter:['class']}));
</script>
</body></html>''')

sys.stdout.write('\n'.join(html))
PYEOF

# Deploy to webroot
ssh "$REMOTE" "
    sudo cp /tmp/archive-gen.html $WEBROOT/archive.html
    sudo chown www-data:www-data $WEBROOT/archive.html
    sudo chmod 644 $WEBROOT/archive.html
    rm -f /tmp/archive-gen.html
    echo '✅ archive.html updated'
"
