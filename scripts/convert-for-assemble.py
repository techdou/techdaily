#!/usr/bin/env python3
"""
Convert pipeline.py output JSON to assemble.py content.json format
"""
import json
import sys
from datetime import datetime

def convert_to_assemble_format(pipeline_data):
    """Convert pipeline.py JSON to assemble.py format."""
    date_str = pipeline_data.get('date', '')
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Build date display and weekday
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[date_obj.weekday()]
    date_display = f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"
    issue = date_str.replace('-', '')
    
    # Build category mapping from overview (num -> category)
    cat_by_num = {}
    for item in pipeline_data.get('overview', []):
        num = item.get('num', '')
        cat = item.get('category', '')
        if num and cat:
            cat_by_num[num] = cat
    
    # Build categories from stories (with category from overview mapping)
    categories = []
    seen_cats = set()
    first_id_by_cat = {}
    
    for story in pipeline_data.get('stories', []):
        num = story.get('num', '')
        cat = cat_by_num.get(num, '')  # Get category from overview mapping
        if cat and cat not in seen_cats:
            seen_cats.add(cat)
            first_id_by_cat[cat] = num
            categories.append({"name": cat, "first_id": num})
    
    # Build briefs from overview
    briefs = []
    for item in pipeline_data.get('overview', []):
        num = item.get('num', '')
        briefs.append({
            "num": num.zfill(2) if num else "",
            "cat": item.get('category', ''),
            "title": item.get('title', '').replace(' ↗', '').replace(f' #{num}', ''),
            "story_id": num
        })
    
    # Build sidebar from stories (grouped by category, using cat_by_num mapping)
    sidebar = []
    cat_items = {}
    for story in pipeline_data.get('stories', []):
        num = story.get('num', '')
        cat = cat_by_num.get(num, '')  # Get category from overview mapping
        title = story.get('title', '').replace(' ↗', '')
        if cat:
            if cat not in cat_items:
                cat_items[cat] = []
            cat_items[cat].append({"id": num, "title": title})
    
    for cat_name, items in cat_items.items():
        sidebar.append({"cat": cat_name, "items": items})
    
    # Build stories (inject category from overview mapping)
    stories = []
    for story in pipeline_data.get('stories', []):
        num = story.get('num', '')
        cat = cat_by_num.get(num, '')  # Get category from overview mapping
        stories.append({
            "id": num,
            "cat": cat,
            "title": story.get('title', '').replace(' ↗', ''),
            "source_url": story.get('link', ''),
            "digest": story.get('summary', ''),
            "images": story.get('images', []),
            "num": num.zfill(2)
        })
    
    return {
        "date": date_str,
        "date_display": date_display,
        "weekday": weekday,
        "issue": issue,
        "cover_image": pipeline_data.get('cover_image', ''),
        "story_count": len(stories),
        "categories": categories,
        "briefs": briefs,
        "sidebar": sidebar,
        "stories": stories,
        "glossary": {}
    }

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 convert-for-assemble.py input.json output.json")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)
    
    assemble_data = convert_to_assemble_format(pipeline_data)
    
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(assemble_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Converted: {sys.argv[1]} → {sys.argv[2]}")
