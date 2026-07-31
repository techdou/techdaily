#!/usr/bin/env python3
"""
TechDaily HTML Assembler

Reads a JSON content file + RSS XML + static template parts → outputs complete HTML.

Usage:
    python3 assemble.py --content content.json --rss daily-rss.xml --output /tmp/today-index.html

Content JSON schema (精简版，不再包含 body_html):
{
  "date": "2026-06-16",
  "date_display": "2026年6月16日",
  "weekday": "星期二",
  "issue": "20260616",
  "cover_image": "https://...",
  "story_count": 7,
  "categories": [{"name": "模型发布", "first_id": "1"}],
  "briefs": [
    {"num": "01", "cat": "模型发布", "title": "精要标题", "story_id": "1"}
  ],
  "sidebar": [
    {"cat": "模型发布", "items": [{"id": "1", "title": "故事标题"}]}
  ],
  "stories": [
    {
      "id": "1", "cat": "模型发布",
      "title": "标题", "source_url": "https://...",
      "digest": "AI 写的摘要（可包含 <span class=tech-term>）",
      "images": ["https://..."],
      "num": "01"
    }
  ],
  "glossary": {"术语": {"tag": "类别", "def": "解释"}}
}

注意：body_html 不再由 AI 生成，assemble.py 从 RSS XML 中自动提取。
"""

import argparse
import json
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HEAD_FILE = PROJECT_ROOT / "templates" / "template-head.html"
TAIL_FILE = PROJECT_ROOT / "templates" / "template-tail.html"

# Fallback to skill directory (backward compatibility)
if not HEAD_FILE.exists():
    HEAD_FILE = PROJECT_ROOT / "assets" / "template-head.html"
if not TAIL_FILE.exists():
    TAIL_FILE = PROJECT_ROOT / "assets" / "template-tail.html"


def esc(s):
    """HTML escape"""
    return html.escape(s, quote=False) if s else ""


# ========================================
# RSS Body Extractor (NEW)
# ========================================
def parse_rss_bodies(rss_path):
    """
    Parse RSS XML and extract body HTML for each story.
    Returns dict: {story_num (zero-padded): body_html_string}
    """
    try:
        root = ET.parse(rss_path).getroot()
    except Exception as e:
        print(f"   ⚠️  RSS parse error: {e}")
        return {}

    ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
    channel = root.find('channel')
    items = channel.findall('item') if channel is not None else []

    if not items:
        return {}

    # Use the first (latest) item
    target_item = items[0]

    content_elem = target_item.find('content:encoded', ns)
    if content_elem is None:
        content_elem = target_item.find('{http://purl.org/rss/1.0/modules/content/}encoded')

    html_content = content_elem.text if content_elem is not None else ""
    if not html_content:
        return {}

    bodies = {}
    parts = html_content.split('<hr>')

    for part in parts:
        # Match story number in <code>#N</code> after the title link
        h2_match = re.search(
            r'<h[23]>\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>\s*<code[^>]*>#(\d+)</code>\s*</h[23]>',
            part, re.DOTALL
        )
        if not h2_match:
            continue

        story_num = h2_match.group(3).zfill(2)  # "1" → "01"

        # Extract body paragraphs (<p> tags), excluding blockquote and related links
        p_matches = re.finditer(r'<p>(.*?)</p>', part, re.DOTALL)
        body_parts = []
        for m in p_matches:
            p_inner = m.group(1)
            # Skip "相关链接" / "Related" sections
            if re.search(r'相关链接|Related', p_inner, re.I):
                break
            # Remove <img> tags to avoid duplicate with story-images
            p_inner = re.sub(r'<img[^>]*>', '', p_inner)
            # Skip empty paragraphs after removing images
            if not p_inner.strip():
                continue
            body_parts.append(f'<p>{p_inner}</p>')

        if body_parts:
            # Limit to first 6 paragraphs to keep page size reasonable
            bodies[story_num] = '\n'.join(body_parts[:6])

    print(f"   ✅ RSS bodies extracted: {len(bodies)} stories")
    return bodies


# ========================================
# HTML Builders
# ========================================
def build_sidebar(sidebar_data):
    """Build sidebar navigation HTML"""
    items = []
    for cat in sidebar_data:
        cat_name = esc(cat["cat"])
        links = []
        for item in cat["items"]:
            links.append(
                f'    <span class="sidebar-link" onclick="scrollToStory(\'{item["id"]}\'); toggleSidebar()">'
                f'{item["id"]}. {esc(item["title"])}</span>'
            )
        items.append(
            f'  <div class="sidebar-cat">\n'
            f'    <div class="sidebar-cat-name">{cat_name}</div>\n'
            + "\n".join(links) +
            f'\n  </div>'
        )
    return "\n".join(items)


def build_cat_pills(categories):
    """Build category pill buttons"""
    pills = []
    first = True
    for cat in categories:
        story_id = cat.get("first_id", "1")
        active = " active" if first else ""
        pills.append(
            f'<span class="cat-pill{active}" onclick="scrollToStory(\'{story_id}\')">{esc(cat["name"])}</span>'
        )
        first = False
    return "\n".join(pills)


def build_briefs(briefs):
    """Build today's brief grid items"""
    items = []
    for b in briefs:
        items.append(
            f"    <div class=\"brief-item\" onclick=\"scrollToStory('{b['story_id']}')\">\n"
            f"      <div class=\"brief-head\">\n"
            f"        <span class=\"brief-num\">{b['num']}</span>\n"
            f"        <span class=\"brief-cat\">{esc(b['cat'])}</span>\n"
            f"      </div>\n"
            f"      <h3 class=\"brief-title\">{esc(b['title'])}</h3>\n"
            f"    </div>"
        )
    return "\n".join(items)


def build_stories(stories, rss_bodies=None):
    """Build detailed story articles. body_html comes from RSS if available."""
    articles = []
    rss_bodies = rss_bodies or {}

    for s in stories:
        # Determine body: RSS first, fallback to story's own body_html (for backward compat)
        story_num = s.get("num", s.get("id", "")).zfill(2)
        body_html = rss_bodies.get(story_num, s.get("body_html", ""))

        # Images
        images_html = ""
        if s.get("images"):
            cls = "story-images story-images--multiple" if len(s["images"]) > 1 else "story-images"
            imgs = [f'<img src="{url}" alt="配图" loading="lazy">' for url in s["images"]]
            images_html = f'<div class="{cls}">{"".join(imgs)}</div>'

        articles.append(
            f'<article class="story" id="story-{s["id"]}">\n'
            f'  <div class="story-header">\n'
            f'    <div class="story-num">{s["id"]}</div>\n'
            f'    <div class="story-title-block">\n'
            f'      <div class="story-categories"><span class="story-cat">{esc(s["cat"])}</span></div>\n'
            f'      <h2 class="story-title"><a href="{s["source_url"]}" target="_blank">{esc(s["title"])}</a></h2>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'  <div class="story-summary">{s["digest"]}</div>\n'
            f'  {images_html}\n'
            f'  <div class="story-body">{body_html}</div>\n'
            f'</article>'
        )
    return "\n".join(articles)


def build_glossary_injection(glossary):
    """Build GLOSSARY injection script"""
    if not glossary:
        return ""
    return f'<script>window.GLOSSARY = {json.dumps(glossary, ensure_ascii=False, indent=2)};</script>'


# ========================================
# Main Assembly
# ========================================
def assemble(content, head_html, tail_html, rss_bodies=None):
    """Assemble complete HTML page"""
    date = content["date"]
    date_display = content["date_display"]
    weekday = content.get("weekday", "")
    issue = content.get("issue", date.replace("-", ""))
    cover = content.get("cover_image", "")
    categories = content.get("categories", [])
    sidebar = content.get("sidebar", [])
    briefs = content.get("briefs", [])
    stories = content.get("stories", [])
    glossary = content.get("glossary", {})

    # Build dynamic sections
    sidebar_html = build_sidebar(sidebar)
    pills_html = build_cat_pills(categories)
    briefs_html = build_briefs(briefs)
    stories_html = build_stories(stories, rss_bodies)
    glossary_script = build_glossary_injection(glossary)

    # Inject audio URL and page date
    date_parts = date.split('-')
    audio_url = f"https://news.techdou.com/{date_parts[0]}/{date_parts[1]}/{date_parts[2]}/audio.mp3"
    body_date_attr = f'data-date="{date}"'

    # Body template
    body = f'''<body {body_date_attr}>
<!-- Reading Progress Bar -->
<div class="reading-progress-container">
  <div class="reading-progress-bar" id="readingProgressBar"></div>
</div>

<!-- FLOATING NAV -->
<div class="float-nav">
  <button class="float-btn" onclick="toggleSidebar()" title="目录">☰</button>
</div>
<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
<nav class="sidebar" id="sidebar">
  <div class="sidebar-title">📰 目录</div>
{sidebar_html}
</nav>

<!-- MASTHEAD -->
<header class="masthead">
  <div class="masthead-inner">
    <div class="masthead-brand">
      <div class="masthead-title">Tech<span class="accent">Daily</span></div>
      <div class="masthead-sub">— 每日科技快报</div>
    </div>
    <div class="masthead-nav">
      <a href="/archive.html" class="masthead-nav-link archive-link">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="3" cy="3" r="1.5"/><circle cx="3" cy="8" r="1.5"/><circle cx="3" cy="13" r="1.5"/><path d="M7 4h6M7 9h6M7 14h6" stroke-linecap="round"/></svg>
        <span>往期回顾</span>
      </a>
    </div>
    <div class="masthead-date">{date_display}<br><span style="font-family:var(--font-serif);font-style:italic">{weekday}</span></div>
  </div>
</header>

<!-- HERO -->
<section class="hero">
  <img class="hero-cover" src="{cover}" alt="今日封面" loading="eager">
  <div class="hero-bar">
    <span class="hero-issue">第 {issue} 期 · {date_display}</span>
  </div>
</section>

<!-- CATEGORY PILLS -->
<div class="cat-nav">
{pills_html}
</div>

<!-- TODAY'S BRIEF -->
<section class="brief-section" id="brief">
  <div class="brief-header">
    <div class="brief-title">今日精要</div>
  </div>
  <div class="audio-player" id="audioPlayer">
    <button class="audio-play-btn" id="playBtn" onclick="togglePlay()">
      <svg viewBox="0 0 24 24" id="playIcon"><polygon points="5,3 19,12 5,21"/></svg>
      <svg viewBox="0 0 24 24" id="pauseIcon" style="display:none"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
    </button>
    <div class="audio-info">
      <div class="audio-label">🎙 今日精要播报</div>
      <div class="audio-desc">1-2分钟速览今日 AI 要闻</div>
    </div>
    <div class="audio-progress-wrap">
      <div class="audio-track"><div class="audio-fill" id="progressFill"></div></div>
      <span class="audio-time" id="audioTime">0:00</span>
    </div>
  </div>
  <div class="brief-grid">
{briefs_html}
  </div>
</section>

<!-- SECTION DIVIDER -->
<div class="section-divider">
  <div class="section-divider-inner">
    <span class="section-label">详细报道</span>
  </div>
</div>

<!-- STORIES -->
<section class="stories" id="stories">
{stories_html}
</section>

<!-- Back to Top -->
<button class="back-to-top" id="backToTop" onclick="scrollToTop()" aria-label="回到顶部">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
</button>

<footer class="footer">
  <div class="footer-brand">Tech<span class="accent">Daily</span></div>
  <div class="footer-info">© 2026 techdou.com</div>
</footer>

<!-- MODAL -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header"><span class="modal-term" id="modalTerm"></span><button class="modal-close" onclick="closeModal()">&times;</button></div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<!-- Image Lightbox -->
<div class="image-lightbox" id="imageLightbox" aria-hidden="true">
  <div class="image-lightbox-inner">
    <button class="image-lightbox-close" type="button" aria-label="关闭图片预览" onclick="closeImageLightbox()">×</button>
    <img id="imageLightboxImg" src="" alt="放大预览">
    <div class="image-lightbox-caption" id="imageLightboxCaption"></div>
  </div>
</div>

<!-- DouknowAI Pet -->
<iframe src="/pet.html?v=5" class="pet-iframe" id="petIframe" title="DouknowAI Pet"></iframe>

{glossary_script}
<script>window.TechDailyAudioUrl = "{audio_url}";</script>
</body>'''

    # Update <title> in head
    head_html = head_html.replace(
        "<title>TechDaily · 2026年6月15日</title>",
        f"<title>TechDaily · {date_display}</title>"
    )

    return head_html + "\n" + body + "\n" + tail_html + "\n"


def main():
    parser = argparse.ArgumentParser(description="Assemble TechDaily HTML")
    parser.add_argument("--content", required=True, help="Path to content JSON file")
    parser.add_argument("--rss", help="Path to RSS XML file (for body extraction)")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--head", default=str(HEAD_FILE), help="Override head template")
    parser.add_argument("--tail", default=str(TAIL_FILE), help="Override tail template")
    args = parser.parse_args()

    with open(args.content, "r", encoding="utf-8") as f:
        content = json.load(f)

    with open(args.head, "r", encoding="utf-8") as f:
        head_html = f.read()
    with open(args.tail, "r", encoding="utf-8") as f:
        tail_html = f.read()

    # Extract bodies from RSS if provided
    rss_bodies = None
    if args.rss and Path(args.rss).exists():
        print(f"📄 Reading RSS: {args.rss}")
        rss_bodies = parse_rss_bodies(args.rss)

    html_output = assemble(content, head_html, tail_html, rss_bodies)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_output)

    size_kb = len(html_output) / 1024
    print(f"✅ Assembled: {args.output} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
