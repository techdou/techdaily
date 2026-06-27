# 📰 TechDaily

> AI 驱动的每日科技日报 — RSS → AI 摘要 → TTS 音频 → 自动部署

**线上地址**：[news.techdou.com](https://news.techdou.com)

## ✨ 特性

- **全自动流水线**：RSS 抓取 → 解析 → HTML 生成 → TTS 音频 → GitHub 版本管理 → 服务器部署
- **报纸式排版**：精仿报刊风格，分类导航 + 术语弹窗 + 图片灯箱 + 阅读进度
- **TTS 语音播报**：每日生成中文新闻播报音频（MiniMax Podcast_girl 音色）
- **往期回顾**：按月归档，支持「最近 7 天」/「全部」筛选
- **吉祥物**：金豆宠物互动（桌面端）
- **容错机制**：RSS 不可用时自动部署占位页，1 小时后重试

## 🏗️ 项目结构

```
techdaily/
├── scripts/                    # 构建脚本
│   ├── pipeline.py             # 全自动流水线（主入口）
│   ├── assemble.py             # HTML 组装器（template-head + content + template-tail）
│   ├── deploy.sh               # 部署脚本（git push → server pull）
│   └── gen-archive.sh          # 归档页生成器
├── templates/                  # HTML 模板
│   ├── template-head.html      # CSS 模板（68KB）
│   ├── template-tail.html      # JS 模板（37KB）
│   └── no-update.html          # RSS 失败占位页
├── public/                     # 静态网站根目录
│   ├── 2026/06/DD/             # 每日日报（index.html + audio.mp3）
│   ├── archive.html            # 往期回顾
│   ├── assets/                 # Logo、favicon、宠物素材
│   └── pet.html / pet.js       # 吉祥物
├── docs/                       # 参考文档
│   ├── content-schema.md       # 数据结构说明
│   └── rss-structure.md        # RSS 源结构
├── SKILL.md                    # OpenClaw Skill 定义
├── LICENSE                     # MIT License
└── README.md                   # 本文件
```

## 🔄 工作流

```
每日 10:00 (CST) cron 触发
    │
    ├─ 1. 抓取 RSS（daily.juya.uk）→ 解析新闻
    ├─ 2. clean_rss_artifacts() 清理 RSS 模板变量
    ├─ 3. assemble.py 组装完整 HTML（template-head + body + template-tail）
    ├─ 4. TTS 合成播报音频（MiniMax）
    ├─ 5. 保存到 public/YYYY/MM/DD/
    ├─ 6. git commit + push（版本管理）
    ├─ 7. 服务器 git pull → rsync 到 webroot
    └─ 8. 更新 archive.html + 微信通知
```

## 🚀 部署

### 自动部署（Cron）

每天 10:00 由 OpenClaw isolated session 自动执行 pipeline.py。

### 手动部署

```bash
# 全自动（推荐）
python3 scripts/pipeline.py --date 2026-06-27

# 仅部署已有文件
bash scripts/deploy.sh 2026-06-27

# 重新生成归档页
bash scripts/gen-archive.sh
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_USER` | `ubuntu` | SSH 用户 |
| `SERVER_HOST` | `43.153.24.30` | 服务器地址 |

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 内容源 | RSS（daily.juya.uk） |
| HTML 模板 | 纯 HTML/CSS/JS，无框架 |
| TTS | MiniMax Speech（Podcast_girl） |
| 版本管理 | Git + GitHub |
| 部署 | Server git pull + rsync → Nginx |
| 自动化 | OpenClaw Cron |

## 📜 License

MIT © [TechDou](https://github.com/DouXiulu)
