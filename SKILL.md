---
name: daily-news
description: "TechDaily 科技日报自动生成与部署。从 RSS 抓取 AI 科技新闻，生成精美 HTML 日报 + TTS 音频播报，部署到 news.techdou.com。触发词：日报、daily news、新闻播报、早报、TechDaily、科技日报、新闻部署。"
---

# Daily News — TechDaily 科技日报

> **项目仓库**: `~/Project/news.techdou.com`
> **线上地址**: https://news.techdou.com
> **定时任务**: 每天 10:00 (Asia/Shanghai)，isolated session，超时 900s

## 架构概览

```
RSS (daily.juya.uk)
  ↓ fetch + parse
pipeline.py → 结构化数据
  ↓ assemble.py (template-head + template-tail)
完整 HTML (~140KB)
  ↓ + TTS 音频 (mmx speech synthesize)
deploy.sh → news.techdou.com/YYYY/MM/DD/
  ↓
gen-archive.sh → 更新 archive.html
```

## 项目结构

```
~/Project/news.techdou.com/
├── SKILL.md                 # 本文件
├── README.md
├── scripts/
│   ├── pipeline.py          # 全自动 Pipeline（主入口）
│   ├── assemble.py          # HTML 组装器（template-head + content + template-tail）
│   ├── deploy.sh            # 部署到服务器
│   └── gen-archive.sh       # 生成 archive.html
├── templates/
│   ├── template-head.html   # CSS 模板（68KB，固定）
│   ├── template-tail.html   # JS 模板（37KB，固定）
│   └── no-update.html       # RSS 失败占位页
├── docs/
│   ├── content-schema.md    # content.json 字段说明
│   └── rss-structure.md     # RSS 结构参考
└── public/                  # 部署到服务器的静态文件
    ├── 2026/06/DD/          # 每日日报 (index.html + audio.mp3)
    ├── archive.html         # 往期回顾
    ├── 404.html
    ├── pet.html / pet.js    # 吉祥物
    └── assets/              # logo、favicon、宠物素材
```

## 每日发布流程

### 全自动 Pipeline（推荐）

```bash
python3 ~/Project/news.techdou.com/scripts/pipeline.py --date 2026-06-27
```

自动完成：RSS 抓取 → 解析 → 播报稿 → TTS → HTML 生成（assemble.py 完整模板）→ 部署 → 归档

### 可选参数

| 参数 | 说明 |
|------|------|
| `--date YYYY-MM-DD` | 指定日期（默认最新） |
| `--skip-tts` | 跳过音频生成 |
| `--skip-deploy` | 跳过部署 |
| `--parse-only` | 仅解析 RSS，输出 JSON |

### 手动部署（如需）

```bash
# 部署指定日期
bash ~/Project/news.techdou.com/scripts/deploy.sh 2026-06-27

# 重新生成归档页
bash ~/Project/news.techdou.com/scripts/gen-archive.sh
```

## TTS 音频规范

| 项目 | 值 |
|------|-----|
| 工具 | `mmx speech synthesize` |
| 音色 | `Podcast_girl` (MiniMax) |
| 格式 | mp3, 32kHz, 128kbps |
| 时长 | 220-300 秒 |
| 开头 | "欢迎收听 TechDaily 每日科技快报" |
| 结尾 | "感谢收听，我们明天再见" |
| 输入 | 必须 `--text-file`（stdin 会截断） |

## HTML 模板架构

pipeline.py 内部调用 `assemble.py` 生成 HTML：

1. pipeline.py 解析 RSS → 结构化数据
2. 构建 content.json 格式（briefs/stories/sidebar/categories）
3. 调用 `assemble.assemble(content, head, tail, rss_bodies)`
4. assemble.py 从 `templates/template-head.html` + 动态 body + `templates/template-tail.html` 拼装
5. 自动注入：audio URL、body data-date、GLOSSARY JSON

**模板文件不要改**，除非明确要做 UI 升级。

## 部署流程（GitHub 版本管理）

```
Mac 本地生成 → public/YYYY/MM/DD/ → git commit + push GitHub → 服务器 git pull + rsync webroot
```

- **本地**：pipeline.py 生成到 `public/` 目录
- **GitHub**：`github.com/techdou/techdaily` 做版本管理
- **服务器**：`/var/www/news.techdou.com-repo/` git pull → rsync 到 webroot
- **同步脚本**：服务器 `/var/www/sync-from-git.sh`

## 错误处理

| 场景 | 处理 |
|------|------|
| RSS 不可达 | 部署 no-update.html + 1h 后自动重试 |
| 无今日内容 | 部署 no-update.html |
| TTS 失败 | 重试 3 次（间隔 10s），仍失败 → 检查服务器已有音频 → 只部署 HTML |
| 部署失败 | 保留本地，通知用户 |

## Cron 配置

```json
{
  "name": "daily-news",
  "schedule": { "kind": "cron", "expr": "0 10 * * *", "tz": "Asia/Shanghai" },
  "payload": { "kind": "agentTurn", "message": "执行每日日报生成流程，运行 pipeline.py" },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "openclaw-weixin" }
}
```

## 关键教训

| 日期 | 教训 |
|------|------|
| 06-25 | `mmx speech synthesize` 从 stdin 读取会截断 → 必须 `--text-file` |
| 06-25 | RSS 的 `<h2>` 可能变 `<h3>` → 解析器同时匹配 `<h[23]>` |
| 06-25 | RSS 403 → 必须带 User-Agent 头 |
| 06-26 | 音频路径必须用日期目录，不能用顶层 `broadcast.mp3` |
| 06-27 | pipeline 必须用 assemble.py 完整模板，不能用简陋模板 |
| 06-27 | RSS 源含 `{var\|"default"}` 条件语法 → `clean_rss_artifacts()` 自动清理 |
| 06-27 | archive.html 日期以目录路径为准，不读 HTML title |
