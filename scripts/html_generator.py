#!/usr/bin/env python3
"""
HTML generator for TechDaily Pipeline.
Uses external template file for maintainability.
"""
import json
from datetime import datetime
from pathlib import Path
import re
from html import unescape


def strip_html(text):
    """Remove HTML tags, return plain text."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return unescape(clean).strip()


def highlight_terms(text, glossary):
    """Wrap tech terms with clickable spans."""
    terms = sorted(glossary.keys(), key=len, reverse=True)
    escaped = [re.escape(t) for t in terms]
    pattern = '(' + '|'.join(escaped) + ')'

    def replace(m):
        term = m.group(1)
        return f'<span class="tech-term" onclick="openModal(\'{term}\')">{term}</span>'

    parts = re.split(r'(<[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            result.append(part)
        else:
            result.append(re.sub(pattern, replace, part))
    return ''.join(result)


def _build_cat_pills(data):
    """Build category pill buttons."""
    categories = {}
    for item in data['overview']:
        cat = item.get('category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item.get('num', ''))
    return '\n'.join(
        f'<span class="cat-pill" onclick="scrollToStory(\'{nums[0]}\')">{cat}</span>'
        for cat, nums in categories.items()
    )


def _build_brief_html(data, glossary):
    """Build brief items HTML."""
    brief_items = []
    for item in data['overview']:
        num = item.get('num', '')
        cat = item.get('category', '')
        title = item.get('title', '').replace(' ↗', '').replace(f' #{num}', '')
        brief_items.append(f'''
    <div class="brief-item" onclick="scrollToStory('{num}')">
      <div class="brief-head">
        <span class="brief-num">{num}</span>
        <span class="brief-cat">{cat}</span>
      </div>
      <div class="brief-title">{highlight_terms(title, glossary)}</div>
    </div>''')
    return '\n'.join(brief_items)


def _build_stories_html(data, glossary):
    """Build stories HTML."""
    stories_html = []
    for story in data['stories']:
        num = story['num']
        cats = [o['category'] for o in data['overview'] if o.get('num') == num]
        cat_tags = ''.join(f'<span class="story-cat">{c}</span>' for c in cats)
        
        imgs = story.get('images', [])
        imgs_html = ''
        if imgs:
            img_tags = ''.join(f'<img src="{u}" alt="配图" loading="lazy">' for u in imgs)
            imgs_html = f'<div class="story-images">{img_tags}</div>'
        
        summary = highlight_terms(story.get('summary', ''), glossary)
        body_text = highlight_terms(story.get('full_text', ''), glossary)
        body_paragraphs = ''.join(f'<p>{p}</p>' for p in body_text.split('\n\n') if p.strip())
        
        stories_html.append(f'''<article class="story" id="story-{num}">
  <div class="story-header">
    <div class="story-num">{num}</div>
    <div class="story-title-block">
      <div class="story-categories">{cat_tags}</div>
      <h2 class="story-title"><a href="{story['link']}" target="_blank">{story['title']}</a></h2>
    </div>
  </div>
  <div class="story-summary">{summary}</div>
  {imgs_html}
  <div class="story-body">{body_paragraphs}</div>
</article>''')
    return '\n'.join(stories_html)


def _build_audio_section(audio_url):
    """Build audio player HTML."""
    if audio_url:
        return f'''<div class="audio-player" id="audioPlayer">
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
    <span class="audio-time" id="audioTime">—:—</span>
  </div>
</div>'''
    return '''<div class="audio-player audio-disabled">
  <div class="audio-info">
    <div class="audio-label">🎙 今日精要播报</div>
    <div class="audio-desc">音频生成中...</div>
  </div>
</div>'''


def _build_sidebar_html(data):
    """Build sidebar navigation grouped by category."""
    cat_groups = {}
    for item in data['overview']:
        cat = item.get('category', '其他')
        if cat not in cat_groups:
            cat_groups[cat] = []
        cat_groups[cat].append(item)
    
    sections = []
    for cat_name, items in cat_groups.items():
        links = '\n'.join(
            f'<span class="sidebar-link" onclick="scrollToStory(\'{item.get("num", "")}\'); toggleSidebar()">{item.get("num", "")}. {item.get("title", "").replace(" ↗", "").replace(f" #{item.get("num", "")}", "")[:30]}...</span>'
            for item in items
        )
        sections.append(
            f'<div class="sidebar-cat">\n'
            f'    <div class="sidebar-cat-name">{cat_name}</div>\n'
            f'{links}\n'
            f'  </div>'
        )
    return '\n'.join(sections)


def validate_html(html):
    """Validate generated HTML has all required elements."""
    # When no audio URL, audio player may be disabled (OK)
    has_audio = 'id="audioPlayer"' in html or 'audio-disabled' in html
    
    required = {
        'pet iframe': 'id="petIframe"' in html,
        'back-to-top button': 'id="backToTop"' in html,
        'sidebar categories': 'class="sidebar-cat-name"' in html,
        'audio player (or disabled)': has_audio,
        'modal overlay': 'id="modalOverlay"' in html,
        'header nav link': 'masthead-nav-link' in html,
        'glossary JS': 'const GLOSSARY' in html,
    }
    issues = []
    for name, present in required.items():
        if not present:
            issues.append(f"  ❌ Missing: {name}")
    if issues:
        print("   ⚠️  HTML validation warnings:")
        for issue in issues:
            print(issue)
    else:
        print("   ✅ HTML validation passed (all elements present)")
    return len(issues) == 0


def generate_html(data, output_path, glossary, audio_url=None):
    """Generate HTML page from external template."""
    print(f"🎨 Generating HTML...")
    
    # Date info
    date = data['date']
    try:
        dt = datetime.strptime(date, '%Y-%m-%d')
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[dt.weekday()]
        date_display = f"{dt.year}年{dt.month}月{dt.day}日"
    except:
        weekday = ''
        date_display = date
    
    # Load template
    template_path = Path(__file__).parent.parent / "assets" / "pipeline-template.html"
    try:
        template = template_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f"   ❌ Template not found: {template_path}")
        raise
    
    # Build all components
    replacements = {
        '{{DATE_DISPLAY}}': date_display,
        '{{WEEKDAY}}': weekday,
        '{{ISSUE}}': date.replace('-', ''),
        '{{COVER_IMAGE}}': data.get('cover_image', ''),
        '{{CAT_PILLS}}': _build_cat_pills(data),
        '{{BRIEF_HTML}}': _build_brief_html(data, glossary),
        '{{STORIES_HTML}}': _build_stories_html(data, glossary),
        '{{AUDIO_SECTION}}': _build_audio_section(audio_url),
        '{{SIDEBAR_HTML}}': _build_sidebar_html(data),
        '{{GLOSSARY_JSON}}': json.dumps(glossary, ensure_ascii=False),
        '{{AUDIO_URL}}': audio_url or '',
    }
    
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    # Validate before writing
    validate_html(html)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ HTML: {output_path} ({len(html)} bytes)")
    return output_path
