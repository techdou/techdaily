#!/bin/bash
# gen-archive.sh — Regenerate archive.html for TechDaily
# Scans the server's deployed daily pages and generates a clean archive.html
# Usage: bash scripts/gen-archive.sh
set -e

REMOTE="${DEPLOY_SERVER:?Error: DEPLOY_SERVER not set}"
WEBROOT="${DEPLOY_PATH:?Error: DEPLOY_PATH not set}"

ssh "$REMOTE" "python3 - > /tmp/archive-gen.html" << 'PYEOF'
import os, datetime, sys, re
from collections import OrderedDict

WEBROOT = "/var/www/news.techdou.com"
# Only YYYY/MM/DD/index.html paths count as daily reports. Anchored regex
# avoids accidentally picking up unrelated directories that merely start
# with "20" (e.g. backups), and the date validity check below filters the rest.
DATE_PATH = re.compile(r'^(\d{4})/(\d{2})/(\d{2})/index\.html$')
entries = []
for root, dirs, files in os.walk(WEBROOT):
    for fn in files:
        if fn == "index.html":
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, WEBROOT).replace("\\", "/")
            entries.append(rel)

entries = [e for e in entries if DATE_PATH.match(e)]
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>往期回顾 · TechDaily</title>
<meta name="description" content="TechDaily 科技日报往期回顾 — 按月归档的全部历史日报">
<link rel="icon" type="image/svg+xml" href="/assets/logo/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght,0,400;0,700;0,900;1,400&family=Noto+Serif+SC:wght,400;600;700;900&family=DM+Sans:wght,400;500;700&family=JetBrains+Mono:wght,400;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a1a1a;--ink-soft:#2b251f;--ink-muted:#6b6358;--paper:#f5f1e8;--paper-warm:#efe9dc;--paper-card:#fffdf8;--paper-dark:#e0d8c8;--accent:#8b1a1a;--accent-soft:#c44d4d;--accent-light:#e8a0a0;--accent-bg:rgba(139,26,26,0.06);--rule:#c8c0b0;--rule-soft:#ddd6c8;--rose:#d4756e;--rose-soft:#f0d5d2;--rose-bg:rgba(212,117,110,0.06);--gold:#b8935a;--gold-soft:rgba(184,147,90,0.08);--font-serif:'Noto Serif SC','Playfair Display',Georgia,serif;--font-display:'Playfair Display','Noto Serif SC',Georgia,serif;--font-sans:'DM Sans',-apple-system,'PingFang SC',sans-serif;--font-mono:'JetBrains Mono','SF Mono',Consolas,monospace;--shadow-xs:0 1px 2px rgba(43,37,31,0.04);--shadow-sm:0 2px 8px rgba(43,37,31,0.06);--shadow-md:0 8px 24px rgba(43,37,31,0.10);--shadow-lg:0 16px 48px rgba(43,37,31,0.14);--radius-sm:8px;--radius-md:12px;--radius-lg:18px;--radius-xl:28px}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{font-family:var(--font-sans);background:var(--paper);color:var(--ink);line-height:1.6;-webkit-font-smoothing:antialiased;background-image:radial-gradient(circle at 15% 10%,rgba(212,117,110,0.04) 0%,transparent 40%),radial-gradient(circle at 85% 80%,rgba(184,147,90,0.04) 0%,transparent 40%)}
a{color:inherit;text-decoration:none}

/* === HEADER === */
.header{background:linear-gradient(135deg,#1a1a1a 0%,#2b251f 50%,#1a1a1a 100%);color:var(--paper);padding:60px 20px 48px;text-align:center;position:relative;overflow:hidden}
.header::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;background:radial-gradient(ellipse at 30% 0%,rgba(196,77,77,0.18) 0%,transparent 55%),radial-gradient(ellipse at 70% 100%,rgba(184,147,90,0.10) 0%,transparent 50%);pointer-events:none}
.header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent-soft),transparent);opacity:.4}
.header-inner{position:relative;max-width:900px;margin:0 auto}
.header .logo{width:52px;height:52px;border-radius:var(--radius-md);margin:0 auto 20px;display:block;box-shadow:0 4px 16px rgba(196,77,77,0.3)}
.header h1{font-family:var(--font-display);font-size:clamp(2.2rem,5.5vw,3.6rem);font-weight:900;letter-spacing:-0.03em;line-height:1;margin-bottom:12px}
.header h1 .accent{color:var(--accent-soft);font-style:italic;font-weight:400}
.header .sub{font-family:var(--font-serif);font-size:clamp(.92rem,1.5vw,1.08rem);font-style:italic;opacity:.65;letter-spacing:.02em}
.header .ornament{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:18px;opacity:.4}
.header .ornament-line{width:60px;height:1px;background:linear-gradient(90deg,transparent,var(--paper),transparent)}
.header .ornament-dot{width:5px;height:5px;border-radius:50%;background:var(--accent-soft)}

/* === NAV === */
.nav{max-width:900px;margin:0 auto;padding:20px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.back{display:inline-flex;align-items:center;gap:6px;padding:8px 18px;font-family:var(--font-sans);font-size:.85rem;color:var(--ink-soft);border:1px solid var(--rule-soft);border-radius:100px;background:var(--paper-card);transition:all .25s ease;box-shadow:var(--shadow-xs)}
.back:hover{background:var(--accent);color:var(--paper-card);border-color:var(--accent);box-shadow:0 4px 12px rgba(139,26,26,0.2)}
.filter{display:flex;gap:6px;flex-wrap:wrap}
.filter-btn{font-family:var(--font-mono);font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-muted);background:transparent;padding:6px 16px;border-radius:100px;cursor:pointer;transition:all .2s;border:1px solid transparent}
.filter-btn:hover{color:var(--rose);background:var(--rose-bg)}
.filter-btn.active{color:#fff;background:linear-gradient(135deg,var(--accent) 0%,var(--rose) 100%);border-color:transparent;box-shadow:0 2px 8px rgba(139,26,26,0.2)}

/* === CONTAINER === */
.container{max-width:900px;margin:0 auto;padding:36px 20px 60px}

/* === MONTH GROUP === */
.month-group{margin-bottom:44px}
.month-title{font-family:var(--font-display);font-size:1.35rem;font-weight:700;margin-bottom:20px;display:flex;align-items:baseline;gap:12px;letter-spacing:-0.01em}
.month-title .num{color:var(--accent);font-style:italic;font-weight:400}
.month-title .line{flex:1;height:1px;background:linear-gradient(90deg,var(--rule) 0%,transparent 100%)}
.month-title .count{font-family:var(--font-mono);font-size:.7rem;color:var(--ink-muted);font-weight:400;letter-spacing:.03em}

/* === GRID === */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}

/* === CARD === */
.item{background:var(--paper-card);border:1px solid var(--rule-soft);border-radius:var(--radius-lg);padding:22px 20px;cursor:pointer;transition:all .3s cubic-bezier(.4,0,.2,1);display:flex;flex-direction:column;gap:12px;position:relative;overflow:hidden;box-shadow:var(--shadow-xs)}
.item::before{content:'';position:absolute;top:0;left:0;width:100%;height:3px;background:linear-gradient(90deg,var(--accent),var(--rose),var(--gold));transform:scaleX(0);transform-origin:left;transition:transform .35s cubic-bezier(.4,0,.2,1);border-radius:0 0 3px 3px}
.item::after{content:'';position:absolute;bottom:-40px;right:-40px;width:100px;height:100px;border-radius:50%;background:radial-gradient(circle,var(--rose-soft) 0%,transparent 70%);opacity:0;transition:opacity .3s}
.item:hover{box-shadow:var(--shadow-md);transform:translateY(-3px);border-color:var(--rose-soft)}
.item:hover::before{transform:scaleX(1)}
.item:hover::after{opacity:.5}

/* === CARD CONTENT === */
.item-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.item-date{font-family:var(--font-display);font-size:1.65rem;font-weight:900;color:var(--ink);line-height:1;letter-spacing:-0.03em}
.item-date .slash{color:var(--rule);font-weight:300;margin:0 1px}
.item-weekday{font-family:var(--font-serif);font-size:.75rem;color:var(--ink-muted);font-style:italic;white-space:nowrap;margin-top:4px}
.item-body{display:flex;align-items:center;justify-content:space-between;gap:8px}
.item-meta{display:flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:.65rem;color:var(--ink-muted);letter-spacing:.03em;text-transform:uppercase}
.item-meta-dot{width:4px;height:4px;border-radius:50%;background:var(--rose)}
.item-arrow{opacity:0;transition:all .25s;font-size:.9rem;color:var(--accent);transform:translateX(-4px)}
.item:hover .item-arrow{opacity:1;transform:translateX(0)}

/* === FOOTER === */
.footer{max-width:900px;margin:0 auto;padding:28px 20px 48px;text-align:center;position:relative}
.footer::before{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:120px;height:1px;background:linear-gradient(90deg,transparent,var(--rule),transparent)}
.footer-text{font-family:var(--font-mono);font-size:.72rem;color:var(--ink-muted);letter-spacing:.06em}
.footer-text .accent{color:var(--accent);font-weight:600}
.footer-ornament{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:10px;opacity:.3}
.footer-ornament-line{width:40px;height:1px;background:var(--rule)}
.footer-ornament-dot{width:4px;height:4px;border-radius:50%;background:var(--accent-soft)}

/* === ANIMATIONS === */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}

/* Progressive enhancement: cards are visible by default. Only when JS runs
   (html.js) do we hide them until they scroll into view, then fade in. */
html.js .item{opacity:0;transform:translateY(14px);transition:opacity .4s ease,transform .4s ease}
html.js .item.visible{opacity:1;transform:none}
html.js .month-group{opacity:0;transform:translateY(16px);transition:opacity .5s ease,transform .5s ease}
html.js .month-group.visible{opacity:1;transform:none}

/* Keyboard focus parity with hover */
.item:focus-visible{outline:2px solid var(--accent);outline-offset:3px;box-shadow:var(--shadow-md)}
.filter-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.back:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* Empty state */
.empty{grid-column:1/-1;text-align:center;padding:48px 20px;font-family:var(--font-serif);font-style:italic;color:var(--ink-muted);font-size:.95rem}
.empty .accent{color:var(--accent);font-weight:600}

/* === RESPONSIVE === */
@media(max-width:768px){
  .header{padding:44px 16px 36px}
  .nav{padding:16px;flex-direction:column;align-items:stretch;gap:12px}
  .container{padding:28px 16px 40px}
  .grid{grid-template-columns:1fr;gap:12px}
  .item{padding:18px 16px;border-radius:var(--radius-md)}
  .item-date{font-size:1.4rem}
  .month-group{margin-bottom:32px}
}
@media(prefers-reduced-motion:reduce){.item,.month-group{transition:none;animation:none}.item:hover{transform:none}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<img src="/assets/logo/favicon.svg" class="logo" alt="TechDaily" onerror="this.style.display='none'">
<h1>往期<span class="accent">回顾</span></h1>
<div class="sub">— TechDaily 科技日报归档</div>
<div class="ornament"><span class="ornament-line"></span><span class="ornament-dot"></span><span class="ornament-line"></span></div>
</div></header>
<nav class="nav"><a href="/" class="back">← 返回今日日报</a><div class="filter" role="group" aria-label="筛选历史日报"><button class="filter-btn active" data-filter="recent" aria-pressed="true">最近 7 天</button><button class="filter-btn" data-filter="all" aria-pressed="false">全部</button></div></nav>
<main class="container" id="container">''')
html.append('<div id="empty-state" class="empty" hidden>当前筛选下暂无日报，试试切换到 <span class="accent">全部</span></div>')

months = OrderedDict()
for it in items:
    if it["ym"] not in months:
        months[it["ym"]] = []
    months[it["ym"]].append(it)

for ym, month_items in months.items():
    y, m = ym.split('/')
    count = len(month_items)
    html.append(f'<div class="month-group" data-month="{ym}"><div class="month-title"><span class="num">{y} · {m}</span><span class="line"></span><span class="count">{count} 期</span></div><div class="grid">')
    for it in month_items:
        m_val, d_val = it["date_short"].split('.')
        label = f"{it['date_iso']} {it['weekday']} 日报"
        html.append(f'<a class="item" data-date="{it["date_iso"]}" href="{it["url"]}" aria-label="{label}"><div class="item-head"><div class="item-date">{m_val}<span class="slash">.</span>{d_val}</div><div class="item-weekday">{it["weekday"]}</div></div><div class="item-body"><div class="item-meta"><span class="item-meta-dot"></span><span>{it["date_iso"]}</span></div><span class="item-arrow">→</span></div></a>')
    html.append('</div></div>')

html.append('''</main>
<footer class="footer"><div class="footer-ornament"><span class="footer-ornament-line"></span><span class="footer-ornament-dot"></span><span class="footer-ornament-line"></span></div><div class="footer-text">© 2026 <span class="accent">TechDaily</span> · techdou.com</div></footer>
<script>
// Mark JS as active so the progressive-enhancement CSS takes over the
// initial hidden state (cards default to visible for no-JS / crawlers).
document.documentElement.classList.add('js');

const filterBtns=document.querySelectorAll('.filter-btn');
const allItems=Array.from(document.querySelectorAll('.item'));
const allGroups=Array.from(document.querySelectorAll('.month-group'));
const emptyState=document.getElementById('empty-state');

// Parse a YYYY-MM-DD string as a LOCAL date (avoids the UTC-midnight drift
// of new Date("2026-06-26") when compared against the local "now").
function localDate(iso){const[y,m,d]=iso.split('-').map(Number);return new Date(y,m-1,d)}

function applyFilter(f){
  const now=new Date();
  const weekAgo=new Date(now.getFullYear(),now.getMonth(),now.getDate()-7);
  let visible=0;
  allItems.forEach(i=>{
    let show=true;
    if(f==='recent'){show=localDate(i.dataset.date)>=weekAgo}
    i.style.display=show?'':'none';
    if(show)visible++;
  });
  // Hide empty month groups; show non-empty ones.
  allGroups.forEach(g=>{
    const hasVisible=[...g.querySelectorAll('.item')].some(i=>i.style.display!=='none');
    g.style.display=hasVisible?'':'none';
  });
  emptyState.hidden=visible>0;
}
filterBtns.forEach(b=>b.addEventListener('click',()=>{
  filterBtns.forEach(x=>{x.classList.remove('active');x.setAttribute('aria-pressed','false')});
  b.classList.add('active');b.setAttribute('aria-pressed','true');
  applyFilter(b.dataset.filter);
}));
applyFilter('recent');

// Single IntersectionObserver drives both card + month-group fade-in.
// (One observer, not two: the callback adds .visible and detaches itself.)
const io=new IntersectionObserver((entries)=>{
  entries.forEach(e=>{
    if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target)}
  });
},{threshold:0.06});
[...allItems,...allGroups].forEach((el,i)=>{
  el.style.transitionDelay=(i%20*30)+'ms';  // stagger within a batch, cap to avoid long waits
  io.observe(el);
});
</script>
<iframe src="/pet.html?v=5" class="pet-iframe" id="petIframe" title="DouknowAI Pet 吉祥物" style="position:fixed;top:0;left:0;width:100vw;height:100vh;border:none;pointer-events:none;z-index:50;background:transparent;overflow:hidden" loading="lazy"></iframe>
</body></html>''')

sys.stdout.write('\n'.join(html))
PYEOF

# Deploy to webroot
ssh "$REMOTE" "
    sudo cp /tmp/archive-gen.html $WEBROOT/archive.html
    sudo chown www-data:www-data $WEBROOT/archive.html
    sudo chmod 644 $WEBROOT/archive.html
    rm -f /tmp/archive-gen.html
    echo '✅ archive.html updated on server'
"

# Pull the same file back into the repo so the local public/archive.html
# stays in sync with what's serving online (the GitHub Pages mirror and git
# history would otherwise drift from the live site).
LOCAL_ARCHIVE="$(cd "$(dirname "$0")/.." && pwd)/public/archive.html"
scp -q "$REMOTE:$WEBROOT/archive.html" "$LOCAL_ARCHIVE"
echo "✅ Pulled archive.html → public/archive.html"
