# Content JSON Schema

AI generates this JSON file. `assemble.py` reads it + static templates → complete HTML.

```json
{
  "date": "2026-06-16",
  "date_display": "2026年6月16日",
  "weekday": "星期二",
  "issue": "20260616",
  "cover_image": "https://...封面图URL",
  "story_count": 7,
  
  "categories": [
    {"name": "模型发布", "first_id": "1"},
    {"name": "技术与洞察", "first_id": "2"}
  ],
  
  "sidebar": [
    {
      "cat": "模型发布",
      "items": [
        {"id": "1", "title": "故事标题"}
      ]
    }
  ],
  
  "briefs": [
    {"num": "01", "cat": "模型发布", "title": "精要一句话", "story_id": "1"}
  ],
  
  "stories": [
    {
      "id": "1",
      "cat": "模型发布",
      "title": "完整标题",
      "source_url": "https://原文链接",
      "digest": "AI写的2-3句摘要，可含 <span class=\"tech-term\" onclick=\"openModal('术语')\">术语</span>",
      "images": ["https://图片URL"],
      "body_html": "<p>正文段落1</p><p>正文段落2</p>"
    }
  ],
  
  "glossary": {
    "术语": {"tag": "类别", "def": "解释"}
  }
}
```

## Field Rules

| 字段 | 说明 |
|------|------|
| `digest` | 可包含 `<span class="tech-term">` 标签 |
| `body_html` | 多个 `<p>` 段落，可含 tech-term 标签和图片 |
| `images` | 空数组 `[]` 表示无图；1 张居中显示；2+ 张横向画廊 |
| `source_url` | 原文链接，点击标题新窗口打开 |
| `glossary` | 当天新闻涉及的术语，key 是术语原文 |

## What AI Writes vs What's Static

| AI 生成 | 模板固定（不读入上下文） |
|---------|----------------------|
| 所有文字内容 | CSS 样式 (~68KB) |
| 图片 URL 选择 | JS 交互逻辑 (~36KB) |
| 术语表 | 页面骨架结构 |
| 播报稿（独立文本文件） | Pet/Lightbox/Modal 组件 |
