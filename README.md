# 📰 TechDaily

> AI 驱动的每日科技日报 — RSS → AI 摘要 → TTS 音频 → 自动部署

**线上地址**：[news.techdou.com](https://news.techdou.com)

## ✨ 特性

- **AI 内容生成**：从 RSS 源自动抓取 → AI 精要/摘要/正文 → 每日科技新闻日报
- **TTS 语音播报**：每日生成中文新闻播报音频
- **报纸式排版**：精仿报刊风格，分类导航 + 术语弹窗 + 移动端适配
- **往期回顾**：按月归档，支持「最近 7 天」/「全部」筛选
- **吉祥物**：金豆宠物互动（桌面端）

## 🏗️ 项目结构

```
news.techdou.com/
├── public/                 # 静态网站根目录（部署到服务器）
│   ├── archive.html        # 往期回顾页
│   ├── 404.html            # 404 页面
│   ├── pet.html / pet.js   # 吉祥物宠物
│   ├── assets/             # Logo、favicon、宠物素材
│   └── 2026/06/DD/         # 每日日报（index.html + audio.mp3）
├── scripts/                # 构建脚本
│   ├── assemble.py         # content.json + 模板 → 完整 HTML
│   └── gen-archive.sh      # 扫描目录 → 生成 archive.html
├── templates/              # HTML 模板（head/tail 分离）
│   ├── template-head.html  # 68KB CSS（固定）
│   └── template-tail.html  # 36KB JS（固定）
├── docs/                   # 参考文档
│   ├── content-schema.md   # content.json 字段说明
│   └── rss-structure.md    # RSS 源结构
├── SKILL.md                # OpenClaw Skill 定义（完整工作流）
└── README.md
```

## 🔄 工作流

```
每日 10:00 (CST)
    │
    ├─ 1. 抓取 RSS → 解析新闻条目
    ├─ 2. AI 生成 content.json（精要、摘要、分类）
    ├─ 3. TTS 合成播报音频
    ├─ 4. assemble.py 组装完整 HTML
    ├─ 5. 部署到云服务器 → news.techdou.com
    ├─ 6. 更新 archive.html
    └─ 7. 微信通知用户
```

## 🚀 部署

**服务器**：腾讯云 Ubuntu（43.153.24.30）
**Web 根目录**：`/var/www/news.techdou.com/`
**域名**：news.techdou.com（DNS → 腾讯云）

```bash
# 部署单日日报
DATE="2026-06-27"
./scripts/deploy.sh $DATE

# 重新生成归档页
bash scripts/gen-archive.sh
```

## 🛠️ 技术栈

- **内容**：RSS + AI（GLM-5 / Gemini）
- **TTS**：MiniMax Speech 2.8（Podcast_girl 音色）
- **前端**：纯 HTML/CSS/JS，无框架
- **部署**：rsync → Nginx
- **自动化**：OpenClaw Cron

## 📜 License

MIT © [TechDou](https://github.com/DouXiulu)
