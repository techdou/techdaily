#!/usr/bin/env python3
"""
TechDaily Pipeline - Full automation from RSS to deployed website.

Flow: Fetch RSS → Parse XML → Extract Data → AI Summarize → Generate HTML → TTS Audio → Deploy

Usage:
    python pipeline.py --date 2026-06-15
    python pipeline.py  # auto-detects today's date
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.request import urlopen
import xml.etree.ElementTree as ET

# Import HTML assembler (full template-head + template-tail)
import assemble as html_assembler

# ========================================
# CONFIG
# ========================================
RSS_URL = "https://daily.juya.uk/rss.xml"
OUTPUT_DIR = Path.home() / "Project" / "daily-news" / "output"
AUDIO_DIR = OUTPUT_DIR
STATE_FILE = Path.home() / ".openclaw" / "skills" / "daily-news" / "state.json"

# MMX voice
TTS_VOICE = "Podcast_girl"
TTS_FORMAT = "mp3"

# Deploy config (override via environment variables in production)
DEPLOY_SUBDOMAIN = os.environ.get('DEPLOY_SUBDOMAIN', 'news')
DOMAIN = os.environ.get('DEPLOY_DOMAIN', 'techdou.com')

# ========================================
# TECH GLOSSARY
# ========================================
GLOSSARY = {
    "蒸馏": {"tag": "Model Training", "def": "Knowledge Distillation，将大模型知识转移到小模型的技术。"},
    "SFT": {"tag": "Fine-tuning", "def": "Supervised Fine-Tuning，监督微调。"},
    "RL": {"tag": "RL", "def": "Reinforcement Learning，强化学习。"},
    "RLHF": {"tag": "Alignment", "def": "基于人类反馈的强化学习。"},
    "Agent": {"tag": "AI Agent", "def": "能自主感知、规划、调用工具的智能体。"},
    "权重": {"tag": "Model", "def": "Weights，神经网络中的可学习参数。"},
    "张量": {"tag": "Math", "def": "Tensor，多维数组，深度学习的基本数据单元。"},
    "KYC": {"tag": "Compliance", "def": "Know Your Customer，身份验证流程。"},
    "Token": {"tag": "LLM", "def": "语言模型处理文本的基本单位。"},
    "出口管制": {"tag": "Policy", "def": "Export Control，政府对技术出口的限制。"},
    "SOTA": {"tag": "Benchmark", "def": "State-of-the-Art，已知最优成绩。"},
    "线性融合": {"tag": "Model Merge", "def": "Linear Model Merging，权重按比例混合。"},
    "fable": {"tag": "AI Model", "def": "Anthropic 前沿模型。"},
    "Mythos": {"tag": "AI Model", "def": "Anthropic 前沿模型。"},
    "Seedance": {"tag": "Video", "def": "字节跳动 AI 视频生成模型。"},
    "剪映": {"tag": "Tool", "def": "字节跳动视频编辑工具。"},
    "Qwen": {"tag": "Open Model", "def": "阿里通义千问开源模型。"},
    "Gemini": {"tag": "AI Model", "def": "Google DeepMind 多模态模型。"},
    "Nex": {"tag": "AI Model", "def": "开源模型公司。"},
    "Anthropic": {"tag": "Company", "def": "AI 安全公司，Claude 开发者。"},
    "OpenAI": {"tag": "Company", "def": "ChatGPT 开发者。"},
}


def strip_html(text):
    """Remove HTML tags, return plain text."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return unescape(clean).strip()


def clean_rss_artifacts(text):
    """Remove {var|alternative} template artifacts from RSS source.

    The RSS feed (daily.juya.uk) uses a conditional syntax like:
      {部分用户|"部分用户"}  → keep first part: 部分用户
      {/|或}            → keep first part: /
      {2|两}            → keep first part: 2
    We keep the first segment (before |) and discard the alternative.
    """
    if not text:
        return text
    # Match {content|alternative} - keep content (first part)
    def replace_artifact(m):
        inner = m.group(1)
        # Split on | and keep first part, strip quotes
        parts = inner.split('|', 1)
        kept = parts[0].strip()
        # Remove surrounding quotes
        if (kept.startswith('"') and kept.endswith('"')) or (kept.startswith("'") and kept.endswith("'")):
            kept = kept[1:-1]
        # Also clean HTML entities
        kept = unescape(kept)
        return kept
    return re.sub(r'\{([^{}]+\|[^{}]+)\}', replace_artifact, text)


def item_title(item):
    """Return an RSS item's stripped title."""
    title = item.find('title')
    return title.text.strip() if title is not None and title.text else ""




# ========================================
# STEP 1: FETCH RSS
# ========================================
def fetch_rss(url=RSS_URL):
    """Fetch RSS XML from URL."""
    print("📡 Fetching RSS...")
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml,application/xml,text/xml,*/*'
        }
    )
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"   ✅ Fetched {len(data)} bytes")
    return data


# ========================================
# STEP 2: PARSE XML
# ========================================
def parse_rss(xml_bytes, target_date=None):
    """
    Parse RSS XML and extract structured data.
    
    Returns dict with:
        date, title, link, cover_image, overview[], stories[]
    """
    print("🔍 Parsing XML...")
    root = ET.fromstring(xml_bytes)
    
    # RSS namespace
    ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
    
    channel = root.find('channel')
    items = channel.findall('item')
    print(f"   Found {len(items)} items")
    
    # Find target item: exact validated date, partial title match, then latest.
    target_item = None
    if target_date:
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError as exc:
            raise ValueError(f"Invalid target date {target_date!r}; expected YYYY-MM-DD") from exc

        for item in items:
            if item_title(item) == target_date:
                target_item = item
                break

        if target_item is None:
            for item in items:
                if target_date in item_title(item):
                    target_item = item
                    print(f"   ⚠️  No exact title match for {target_date}; using partial match: {item_title(item)}")
                    break

        if target_item is None and items:
            target_item = items[0]
            print(f"   ⚠️  No RSS item matched {target_date}; using latest item: {item_title(target_item)}")
    elif items:
        target_item = items[0]

    if target_item is None:
        raise ValueError("No RSS items found")
    
    date = item_title(target_item)
    link = target_item.find('link').text.strip() if target_item.find('link') is not None else ""
    
    # Get content:encoded (full HTML)
    content_elem = target_item.find('content:encoded', ns)
    if content_elem is None:
        # Try without namespace
        content_elem = target_item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
    
    html_content = content_elem.text if content_elem is not None else ""
    
    # Extract cover image
    cover_match = re.search(r'<img\s+src="([^"]+)"', html_content)
    cover_image = cover_match.group(1) if cover_match else ""
    
    # Extract overview sections (h3 + ul)
    overview = []
    h3_pattern = r'<h3>(.*?)</h3>'
    ul_pattern = r'<h3>.*?</h3>\s*<ul>(.*?)</ul>'
    
    categories = re.findall(h3_pattern, html_content, re.DOTALL)
    uls = re.findall(ul_pattern, html_content, re.DOTALL)
    
    for cat, ul_content in zip(categories, uls):
        li_items = re.findall(r'<li>(.*?)</li>', ul_content, re.DOTALL)
        for li in li_items:
            # Extract title text
            title_text = strip_html(li)
            # Extract link
            link_match = re.search(r'<a\s+href="([^"]+)"', li)
            item_link = link_match.group(1) if link_match else ""
            # Extract number
            num_match = re.search(r'#(\d+)', li)
            num = num_match.group(1) if num_match else ""
            
            overview.append({
                'category': clean_rss_artifacts(strip_html(cat)),
                'title': clean_rss_artifacts(title_text),
                'link': item_link,
                'num': num
            })
    
    # Extract detailed stories
    stories = []
    # RSS may use <h2> or <h3> for story titles; try both
    #
    # ⚠️ CRITICAL: 必须使用负向前瞻 (?:(?!</h[23]>).)*? 而不是 .*?
    # 原因：.*? 配合 re.DOTALL 会跨越 </h2> 标签边界，从概览区的 <h2>概览
    # 一路匹配到详情区的第一个 <code>#N</code></h2>，导致所有标题被吞进第一条。
    # 负向前瞻确保匹配内容中不会出现 </h2> 或 </h3>，从而限制在单个标签内。
    # 详见 SKILL.md「正则解析 HTML 的坑」
    story_pattern = re.compile(
        r'<h[23]>\s*((?:(?!</h[23]>).)*?)\s*<code[^>]*>#(\d+)</code>\s*</h[23]>',
        re.DOTALL
    )
    
    for match in story_pattern.finditer(html_content):
        raw_title = match.group(1)
        story_num = match.group(2)
        # Extract link if present, otherwise empty
        link_match = re.search(r'<a\s+href="([^"]+)"', raw_title)
        story_link = link_match.group(1) if link_match else ""
        story_title = strip_html(raw_title)
        
        # Find the content after this match until next story or end
        start_pos = match.end()
        next_match = story_pattern.search(html_content, start_pos)
        end_pos = next_match.start() if next_match else len(html_content)
        part = html_content[start_pos:end_pos]
        
        # Extract blockquote summary
        bq_match = re.search(r'<blockquote>(.*?)</blockquote>', part, re.DOTALL)
        summary = strip_html(bq_match.group(1)) if bq_match else ""
        
        # Extract all images
        imgs = re.findall(r'<img\s+src="([^"]+)"', part)
        
        # Extract body paragraphs (p tags after blockquote, before related links)
        p_texts = re.findall(r'<p>(.*?)</p>', part, re.DOTALL)
        body_parts = []
        for p in p_texts:
            clean = strip_html(p)
            if clean and not clean.startswith('相关链接') and clean not in ['']:
                body_parts.append(clean)
        
        stories.append({
            'num': story_num,
            'title': clean_rss_artifacts(story_title),
            'link': story_link,
            'summary': clean_rss_artifacts(summary),
            'images': imgs,
            'full_text': clean_rss_artifacts('\n\n'.join(body_parts[:6]))  # limit paragraphs
        })
    
    result = {
        'date': date,
        'title': date,
        'link': link,
        'cover_image': cover_image,
        'overview': overview,
        'stories': stories,
    }
    
    # ── Title length validation ──
    # 防止正则匹配异常导致标题内容过长（正常标题 < 80 字）
    # 如果标题超过 100 字，说明解析可能有问题，打印警告
    TITLE_MAX_LEN = 100
    suspicious = [s for s in stories if len(s.get('title', '')) > TITLE_MAX_LEN]
    if suspicious:
        print(f"   ⚠️  WARNING: {len(suspicious)} story title(s) exceed {TITLE_MAX_LEN} chars — possible regex parsing bug!")
        for s in suspicious:
            print(f"       #{s['num']} ({len(s['title'])} chars): {s['title'][:60]}...")
    
    print(f"   ✅ Parsed: {len(overview)} overview items, {len(stories)} stories")
    return result


# ========================================
# STEP 3: AI SUMMARIZE (via OpenClaw model)
# ========================================
def ai_summarize(stories):
    """
    Generate one-sentence summaries for each story using AI.
    For now, use the existing summary from RSS. Future: call LLM API.
    """
    print("🧠 AI Summarize (using RSS summaries)...")
    # The RSS already provides good summaries in blockquote
    # We can enhance them if needed, but for now use as-is
    for story in stories:
        if not story.get('summary') and story.get('full_text'):
            # Fallback: use first sentence of full text
            text = story['full_text']
            first_sentence = text.split('。')[0] + '。' if '。' in text else text[:100]
            story['summary'] = first_sentence
    print("   ✅ Summaries ready")
    return stories


# ========================================
# STEP 4: GENERATE BROADCAST SCRIPT
# ========================================
def generate_broadcast_script(data):
    """Generate spoken broadcast script (1-2 minutes)."""
    print("📝 Generating broadcast script...")
    date = data['date']
    stories = data['stories']
    
    lines = [
        f"欢迎收听 TechDaily 每日科技快报。今天是 {date}。",
        "",
        f"今日共有 {len(stories)} 条科技要闻。",
        ""
    ]
    
    for i, story in enumerate(stories, 1):
        summary = story.get('summary', story['title'])
        # Truncate to ~100 chars for spoken flow
        brief = summary[:120] if len(summary) > 120 else summary
        lines.append(f"第 {i} 条，{brief}")
    
    lines.extend(["", "以上就是今日 TechDaily 的全部内容。感谢收听，我们明天再见。"])
    
    script = '\n'.join(lines)
    print(f"   ✅ Script: {len(script)} chars")
    return script


# ========================================
# STEP 5: TTS (MMX Speech Synthesize)
# ========================================
def synthesize_audio(script, output_path, voice=TTS_VOICE, max_retries=3):
    """Use MMX CLI to generate MP3 audio with retry."""
    print(f"🎙️  Synthesizing audio...")
    
    # Write script to temp file
    tmp_txt = f"/tmp/tts_{os.path.basename(output_path)}.txt"
    with open(tmp_txt, 'w', encoding='utf-8') as f:
        f.write(script)
    
    for attempt in range(1, max_retries + 1):
        cmd = [
            "mmx", "speech", "synthesize",
            "--text-file", tmp_txt,
            "--voice", voice,
            "--format", TTS_FORMAT,
            "--sample-rate", "32000",
            "--bitrate", "128000",
            "--out", output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            os.unlink(tmp_txt)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"   ✅ Audio: {output_path} ({size_kb:.1f} KB)")
            return True
        
        print(f"   ⚠️  TTS attempt {attempt}/{max_retries} failed: {result.stderr.strip()}")
        if attempt < max_retries:
            print(f"   ⏳ Retrying in 10s...")
            import time
            time.sleep(10)
    
    os.unlink(tmp_txt)
    print(f"   ❌ TTS failed after {max_retries} attempts. Deploying without audio.")
    return False


# ========================================
# STEP 6: GENERATE HTML
# ========================================
# ========================================
# STEP 7: DEPLOY
# ========================================
def deploy_site(subdomain, source_file, audio_file=None, date=None):
    """Deploy via GitHub: copy to public/ → git push → server git pull."""
    print(f"🚀 Deploying to {subdomain}.{DOMAIN} via GitHub...")
    
    if date is None:
        date = Path(source_file).stem
    
    project_root = Path.home() / "Project" / "news.techdou.com"
    y, m, d = date.split('-')
    date_path = f"{y}/{m}/{d}"
    public_dir = project_root / "public" / date_path
    public_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Copy HTML to public/
    import shutil
    shutil.copy2(source_file, str(public_dir / "index.html"))
    print(f"   ✅ HTML → public/{date_path}/index.html")
    
    # 2. Copy audio to public/ (if exists)
    if audio_file and os.path.exists(audio_file):
        shutil.copy2(audio_file, str(public_dir / "audio.mp3"))
        print(f"   ✅ Audio → public/{date_path}/audio.mp3")
    
    # 3. Git commit + push
    result = subprocess.run(
        ["bash", "-c", f"cd {project_root} && git add -A && "
         f"if ! git diff --cached --quiet; then git commit -m 'daily: deploy {date}'; fi && "
         f"git push origin main"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"   ❌ Git push failed: {result.stderr.strip()}")
        return False
    print(f"   ✅ Pushed to GitHub")
    
    # 4. Server: git pull + sync
    server_user = os.environ.get('DEPLOY_USER', os.environ.get('SERVER_USER', ''))
    server_host = os.environ.get('DEPLOY_HOST', os.environ.get('SERVER_HOST', ''))
    sync_result = subprocess.run(
        ["ssh", f"{server_user}@{server_host}", "bash /var/www/sync-from-git.sh"],
        capture_output=True, text=True
    )
    if sync_result.returncode != 0:
        print(f"   ❌ Server sync failed: {sync_result.stderr.strip()}")
        return False
    print(sync_result.stdout.strip())
    
    # 5. Update symlink
    remote_dir = f"/var/www/{subdomain}.{DOMAIN}"
    subprocess.run(
        ["ssh", f"{server_user}@{server_host}",
         f"sudo ln -sfn {date_path}/index.html {remote_dir}/index.html"],
        capture_output=True, text=True
    )
    
    # 6. Regenerate archive
    subprocess.run(
        ["bash", str(project_root / "scripts" / "gen-archive.sh")],
        capture_output=True, text=True
    )
    
    # 7. Health check
    deploy_url = f"https://{subdomain}.{DOMAIN}"
    print(f"🔎 Health checking {deploy_url}...")
    try:
        with urllib.request.urlopen(deploy_url, timeout=30) as resp:
            print(f"   ✅ Health check OK: HTTP {resp.status}")
    except Exception as exc:
        print(f"   ⚠️  Health check failed: {exc}")
        return False
    
    return True


# ========================================
# STEP 6b: Build content.json for assemble.py
# ========================================
def _generate_full_html(data, output_path, glossary, audio_url, rss_xml_bytes):
    """Generate HTML using assemble.py with full template-head + template-tail.

    Converts pipeline data format → assemble.py content.json format,
    then calls assemble.assemble() for rich HTML output.
    """
    print("🎨 Generating HTML (full template via assemble.py)...")

    date = data['date']
    try:
        dt = datetime.strptime(date, '%Y-%m-%d')
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[dt.weekday()]
        date_display = f"{dt.year}年{dt.month}月{dt.day}日"
    except Exception:
        weekday = ''
        date_display = date

    # Build categories list (unique, preserving order)
    seen_cats = []
    cat_first = {}
    for item in data['overview']:
        cat = item.get('category', '其他')
        if cat not in seen_cats:
            seen_cats.append(cat)
            cat_first[cat] = item.get('num', '1')
    categories = [{'name': c, 'first_id': cat_first[c]} for c in seen_cats]

    # Build briefs
    briefs = []
    for item in data['overview']:
        num = item.get('num', '')
        title = item.get('title', '').replace(' ↗', '').replace(f' #{num}', '').strip()
        briefs.append({
            'num': num.zfill(2) if num.isdigit() else num,
            'cat': item.get('category', ''),
            'title': title,
            'story_id': num
        })

    # Build sidebar
    sidebar_cats = {}
    for item in data['overview']:
        cat = item.get('category', '其他')
        if cat not in sidebar_cats:
            sidebar_cats[cat] = []
        num = item.get('num', '')
        title = item.get('title', '').replace(' ↗', '').replace(f' #{num}', '').strip()
        sidebar_cats[cat].append({'id': num, 'title': title[:35]})
    sidebar = [{'cat': c, 'items': items} for c, items in sidebar_cats.items()]

    # Build stories in assemble.py format
    stories = []
    for s in data['stories']:
        num = s.get('num', '')
        # Find category from overview
        cat = next((o['category'] for o in data['overview'] if o.get('num') == num), '其他')
        # Build digest with glossary highlighting
        digest = s.get('summary', '')
        # Apply glossary highlighting to digest
        digest = _highlight_terms(digest, glossary)
        stories.append({
            'id': num,
            'cat': cat,
            'title': s.get('title', ''),
            'source_url': s.get('link', ''),
            'digest': digest,
            'images': s.get('images', []),
            'num': num.zfill(2) if num.isdigit() else num
        })

    # Build content.json
    content = {
        'date': date,
        'date_display': date_display,
        'weekday': weekday,
        'issue': date.replace('-', ''),
        'cover_image': data.get('cover_image', ''),
        'categories': categories,
        'briefs': briefs,
        'sidebar': sidebar,
        'stories': stories,
        'glossary': glossary
    }

    # Save RSS to temp file for assemble.py body extraction
    rss_tmp = f'/tmp/pipeline_rss_{date}.xml'
    with open(rss_tmp, 'wb') as f:
        f.write(rss_xml_bytes)

    # Load templates
    project_root = Path(__file__).parent.parent
    head_file = project_root / 'templates' / 'template-head.html'
    tail_file = project_root / 'templates' / 'template-tail.html'

    # Fallback to skill directory
    if not head_file.exists():
        head_file = project_root / 'assets' / 'template-head.html'
    if not tail_file.exists():
        tail_file = project_root / 'assets' / 'template-tail.html'

    with open(head_file, 'r', encoding='utf-8') as f:
        head_html = f.read()
    with open(tail_file, 'r', encoding='utf-8') as f:
        tail_html = f.read()

    # Extract RSS bodies
    rss_bodies = html_assembler.parse_rss_bodies(rss_tmp)

    # Clean RSS bodies of artifacts
    if rss_bodies:
        rss_bodies = {k: clean_rss_artifacts(v) for k, v in rss_bodies.items()}

    # Assemble!
    html_output = html_assembler.assemble(content, head_html, tail_html, rss_bodies)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    # Validate (assemble doesn't have validate_html, skip if not available)
    if hasattr(html_assembler, 'validate_html'):
        html_assembler.validate_html(html_output)

    size_kb = len(html_output) / 1024
    print(f"   ✅ HTML: {output_path} ({size_kb:.1f} KB)")
    return output_path


def _highlight_terms(text, glossary):
    """Wrap tech terms with clickable spans (lightweight version)."""
    if not text or not glossary:
        return text
    import html as html_module
    terms = sorted(glossary.keys(), key=len, reverse=True)
    escaped = [re.escape(t) for t in terms]
    pattern = '(' + '|'.join(escaped) + ')'

    def replace(m):
        term = m.group(1)
        return f'<span class="tech-term" onclick="openModal(\'{term}\')">{term}</span>'

    # Split by HTML tags to avoid modifying inside tags
    parts = re.split(r'(<[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            result.append(part)
        else:
            result.append(re.sub(pattern, replace, part))
    return ''.join(result)


def save_state(data, html_path, audio_path=None, deployed=False, skip_tts=False, skip_deploy=False):
    """Persist the latest pipeline run metadata."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_run_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "date": data.get("date"),
        "title": data.get("title"),
        "stories": len(data.get("stories", [])),
        "overview_items": len(data.get("overview", [])),
        "html_path": str(html_path),
        "audio_path": str(audio_path) if audio_path and os.path.exists(audio_path) else None,
        "deployed": deployed,
        "deployed_url": f"https://{DEPLOY_SUBDOMAIN}.{DOMAIN}" if deployed else None,
        "skip_tts": skip_tts,
        "skip_deploy": skip_deploy,
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 State saved: {STATE_FILE}")


# ========================================
# MAIN PIPELINE
# ========================================
def deploy_no_update(target_date=None):
    """Switch homepage to the pending placeholder (no-update page).

    The pending page lives at public/pending.html and is synced to the server
    via the normal git flow. Here we only flip the root /index.html symlink to
    point at it — no per-date copy, no git push, so the archive stays clean.
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    print(f"📝 Switching homepage to pending (no-update) for {target_date}...")

    server_user = os.environ.get('DEPLOY_USER', os.environ.get('SERVER_USER', ''))
    server_host = os.environ.get('DEPLOY_HOST', os.environ.get('SERVER_HOST', ''))
    remote_dir = f"/var/www/{DEPLOY_SUBDOMAIN}.{DOMAIN}"

    # pending.html is already on the server (synced via git); just repoint symlink.
    result = subprocess.run(
        ["ssh", f"{server_user}@{server_host}",
         f"sudo ln -sfn pending.html {remote_dir}/index.html"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"   ❌ Failed to switch symlink: {result.stderr.strip()}")
        return False

    print(f"   ✅ Homepage → pending.html (https://{DEPLOY_SUBDOMAIN}.{DOMAIN})")
    return True


def retry_pipeline(target_date, skip_tts=False, skip_deploy=False):
    """Retry pipeline after waiting for RSS update."""
    import time
    
    print("=" * 50)
    print("🔄 TechDaily Retry Check")
    print("=" * 50)
    print(f"⏰ Sleeping 3600s before retry ({target_date})...")
    time.sleep(3600)
    
    print("📡 Retrying RSS fetch...")
    xml_data = None
    try:
        xml_data = fetch_rss()
    except Exception as exc:
        print(f"   ❌ RSS fetch still failed: {exc}")
        _write_alert(target_date, f"RSS 1h retry still failed: {exc}")
        return None
    
    try:
        data = parse_rss(xml_data, target_date)
    except Exception as exc:
        print(f"   ❌ RSS parse still failed: {exc}")
        _write_alert(target_date, f"RSS 1h retry parse failed: {exc}")
        return None
    
    if target_date and data.get('date') != target_date:
        print(f"   ⚠️  RSS data date ({data.get('date')}) still doesn't match target ({target_date})")
        _write_alert(target_date, f"RSS 1h retry: still no update for {target_date}")
        return None
    
    # Success! Run full pipeline
    print("   ✅ RSS update found! Running full pipeline...")
    return run_pipeline(target_date=target_date, skip_tts=skip_tts, skip_deploy=skip_deploy)


def _write_alert(target_date, message):
    """Write alert flag for heartbeat to pick up."""
    alert_file = ALERT_DIR / f"rss-alert-{target_date}.flag"
    alert_data = {
        "date": target_date,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "domain": f"https://{DEPLOY_SUBDOMAIN}.{DOMAIN}"
    }
    with open(alert_file, 'w', encoding='utf-8') as f:
        json.dump(alert_data, f, ensure_ascii=False, indent=2)
    print(f"   🚨 Alert written: {alert_file}")


def _spawn_retry(target_date, skip_tts=False, skip_deploy=False):
    """Spawn a detached process to retry RSS check after 1 hour."""
    import subprocess
    import sys
    
    retry_cmd = [
        sys.executable, __file__,
        '--date', target_date,
        '--retry-only',
        '--skip-tts' if skip_tts else '',
        '--skip-deploy' if skip_deploy else ''
    ]
    retry_cmd = [c for c in retry_cmd if c]
    
    print(f"   🔄 Spawning retry process in background...")
    try:
        subprocess.Popen(
            retry_cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        print(f"   ✅ Retry process spawned (PID detached)")
    except Exception as exc:
        print(f"   ❌ Failed to spawn retry: {exc}")


def run_pipeline(target_date=None, skip_tts=False, skip_deploy=False):
    """Run the full pipeline."""
    print("=" * 50)
    print("🦞 TechDaily Pipeline")
    print("=" * 50)
    
    # Check deploy config if deployment is needed
    if not skip_deploy:
        if not os.environ.get('DEPLOY_HOST') and not os.environ.get('SERVER_HOST'):
            print("   ❌ DEPLOY_HOST (or SERVER_HOST) environment variable not set")
            print("   Set DEPLOY_USER, DEPLOY_HOST, DEPLOY_PATH before running.")
            return None
    
    # Step 1: Fetch RSS
    xml_data = None
    try:
        xml_data = fetch_rss()
    except Exception as exc:
        print(f"   ❌ RSS fetch failed: {exc}")
        if not skip_deploy:
            print("🔄 Deploying no-update page and spawning retry...")
            deploy_no_update(target_date)
            _spawn_retry(target_date, skip_tts, skip_deploy)
        return None
    
    # Step 2: Parse
    data = None
    try:
        data = parse_rss(xml_data, target_date)
    except Exception as exc:
        print(f"   ❌ RSS parse failed: {exc}")
        if not skip_deploy:
            print("🔄 Deploying no-update page and spawning retry...")
            deploy_no_update(target_date)
            _spawn_retry(target_date, skip_tts, skip_deploy)
        return None
    
    # Check if parsed data is for the target date
    if target_date and data.get('date') != target_date:
        print(f"   ⚠️  RSS data date ({data.get('date')}) doesn't match target ({target_date})")
        if not skip_deploy:
            print("🔄 Deploying no-update page and spawning retry...")
            deploy_no_update(target_date)
            _spawn_retry(target_date, skip_tts, skip_deploy)
        return None
    
    # Step 3: Summarize
    data['stories'] = ai_summarize(data['stories'])
    
    # Step 4: Generate broadcast script
    script = generate_broadcast_script(data)
    
    # Save script
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUTPUT_DIR / f"{data['date']}_broadcast.txt"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"📝 Script saved: {script_path}")
    
    # Step 5: TTS Audio
    audio_path = OUTPUT_DIR / f"{data['date']}_broadcast.mp3"
    audio_url = None
    
    y, m, d = data['date'].split('-')
    expected_audio_url = f"https://{DEPLOY_SUBDOMAIN}.{DOMAIN}/{y}/{m}/{d}/audio.mp3"
    
    if not skip_tts:
        success = synthesize_audio(script, str(audio_path))
        if success:
            audio_url = expected_audio_url
        else:
            # TTS failed but still set audio_url so player shows (audio may 404 but UI is correct)
            # Check if existing audio is on server
            server_user = os.environ.get('DEPLOY_USER', os.environ.get('SERVER_USER', ''))
            server_host = os.environ.get('DEPLOY_HOST', os.environ.get('SERVER_HOST', ''))
            remote_dir = f"/var/www/{DEPLOY_SUBDOMAIN}.{DOMAIN}"
            check_cmd = [
                "ssh", f"{server_user}@{server_host}",
                f"test -f {remote_dir}/{y}/{m}/{d}/audio.mp3 && echo EXISTS || echo MISSING"
            ]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            if "EXISTS" in result.stdout:
                audio_url = expected_audio_url
                print(f"   ✅ Found existing audio on server: {expected_audio_url}")
    else:
        # If skipping TTS, check if audio already exists on server
        server_user = os.environ.get('DEPLOY_USER', os.environ.get('SERVER_USER', ''))
        server_host = os.environ.get('DEPLOY_HOST', os.environ.get('SERVER_HOST', ''))
        remote_dir = f"/var/www/{DEPLOY_SUBDOMAIN}.{DOMAIN}"
        
        check_cmd = [
            "ssh", f"{server_user}@{server_host}",
            f"test -f {remote_dir}/{y}/{m}/{d}/audio.mp3 && echo EXISTS || echo MISSING"
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if "EXISTS" in result.stdout:
            audio_url = expected_audio_url
            print(f"   ✅ Found existing audio: {expected_audio_url}")
    
    # Step 6: Generate HTML using assemble.py (full template-head + template-tail)
    html_path = OUTPUT_DIR / f"{data['date']}.html"
    _generate_full_html(data, str(html_path), GLOSSARY, audio_url, xml_data)
    
    # Step 7: Deploy
    deployed = False
    if not skip_deploy:
        deployed = deploy_site(DEPLOY_SUBDOMAIN, html_path, audio_path if not skip_tts else None, data['date'])
    
    save_state(data, html_path, audio_path, deployed, skip_tts, skip_deploy)
    
    print("\n" + "=" * 50)
    print("✅ Pipeline complete!")
    print(f"   📄 HTML: {html_path}")
    if not skip_tts:
        print(f"   🎙️  Audio: {audio_path}")
    print(f"   🔗 https://{DEPLOY_SUBDOMAIN}.{DOMAIN}")
    print("=" * 50)
    
    return data


def main():
    parser = argparse.ArgumentParser(description='TechDaily Pipeline')
    parser.add_argument('--date', help='Target date (YYYY-MM-DD), default: latest')
    parser.add_argument('--skip-tts', action='store_true', help='Skip audio generation')
    parser.add_argument('--skip-deploy', action='store_true', help='Skip deployment')
    parser.add_argument('--retry-only', action='store_true', help='Retry check mode (internal use)')
    parser.add_argument('--parse-only', action='store_true', help='Only fetch and parse RSS, print JSON')
    
    args = parser.parse_args()
    
    if args.parse_only:
        xml_data = fetch_rss()
        data = parse_rss(xml_data, args.date)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    
    if args.retry_only:
        retry_pipeline(
            target_date=args.date,
            skip_tts=args.skip_tts,
            skip_deploy=args.skip_deploy
        )
        return
    
    run_pipeline(
        target_date=args.date,
        skip_tts=args.skip_tts,
        skip_deploy=args.skip_deploy
    )


if __name__ == '__main__':
    main()
