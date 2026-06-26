---
name: "daily-news"
description: "AI-driven daily tech news: RSS→JSON→assemble→TTS→deploy. Triggers: 日报, daily news, 新闻播报, 早报."
---

# Daily News — TechDaily 科技日报

> **项目仓库**: `~/Project/news.techdou.com`
> **线上地址**: https://news.techdou.com
> **定时任务**: 每天 10:00 (Asia/Shanghai)，isolated session，超时 900s

## 架构概览

```
RSS (daily.juya.uk)
  ↓ fetch + parse
pipeline.py → pipeline-data.json
  ↓ convert
convert-for-assemble.py → content.json
  ↓ assemble (template-head + content + template-tail)
assemble.py → complete HTML (~130KB)
  ↓ + TTS audio (mmx speech synthesize)
deploy.sh → news.techdou.com/YYYY/MM/DD/
  ↓
gen-archive.sh → 更新 archive.html
```

AI 只写小型 content.json（~5KB），不需要手写完整 HTML。

## 项目结构

```
~/Project/news.techdou.com/
├── public/                  # 部署到服务器的静态文件
│   ├── 2026/06/DD/          # 每日日报 (index.html + audio.mp3)
│   ├── archive.html         # 往期回顾
│   ├── 404.html
│   ├── pet.html / pet.js    # 吉祥物
│   └── assets/              # logo、favicon、宠物素材
├── scripts/
│   ├── pipeline.py          # 全自动 Pipeline（推荐）
│   ├── assemble.py          # Template 组装器
│   ├── convert-for-assemble.py
│   ├── gen-archive.sh       # 生成 archive.html
│   └── deploy.sh            # 部署到服务器
├── templates/
│   ├── template-head.html   # CSS 模板（68KB，固定）
│   ├── template-tail.html   # JS 模板（36KB，固定）
│   ├── pipeline-template.html
│   └── no-update.html       # RSS 失败占位页
├── docs/
│   ├── content-schema.md    # content.json 字段说明
│   └── rss-structure.md     # RSS 结构参考
├── SKILL.md
└── README.md
```

## 每日发布流程

### 方式一：全自动 Pipeline（推荐）

```bash
python3 ~/Project/news.techdou.com/scripts/pipeline.py --date 2026-06-27
```

自动完成：RSS 抓取 → 解析 → 播报稿 → TTS → HTML 生成 → 部署 → 归档

### 方式二：Template 组装（精细控制）

#### 1. 抓取 RSS

```bash
curl -s "https://daily.juya.uk/rss.xml" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  -o /tmp/daily-rss.xml
```

#### 2. 解析 + 转换

```bash
PROJECT=~/Project/news.techdou.com

python3 $PROJECT/scripts/pipeline.py --date 2026-06-27 --parse-only > /tmp/pipeline-output.json 2>&1
sed -n '/^{/,/^}/p' /tmp/pipeline-output.json > /tmp/pipeline-data.json

python3 $PROJECT/scripts/convert-for-assemble.py \
  /tmp/pipeline-data.json /tmp/content.json
```

#### 3. 组装 HTML

```bash
python3 $PROJECT/scripts/assemble.py \
  --content /tmp/content.json \
  --rss /tmp/daily-rss.xml \
  --output /tmp/today-index.html
```

#### 4. TTS 音频

**固定标准**：

| 项目 | 值 |
|------|-----|
| 音色 | `Podcast_girl` (MiniMax) |
| 格式 | mp3, 32kHz, 128kbps |
| 时长 | 220-300 秒（11 条参考） |
| 开头 | "欢迎收听 TechDaily 每日科技快报" |
| 结尾 | "感谢收听，我们明天再见" |

```bash
# 写播报稿 → 合成
mmx speech synthesize --text-file /tmp/broadcast.txt \
  --voice Podcast_girl --output /tmp/audio.mp3
```

#### 5. 部署

```bash
# 复制到项目 public 目录
DATE_PATH=2026/06/27
mkdir -p ~/Project/news.techdou.com/public/$DATE_PATH
cp /tmp/today-index.html ~/Project/news.techdou.com/public/$DATE_PATH/index.html
cp /tmp/audio.mp3 ~/Project/news.techdou.com/public/$DATE_PATH/audio.mp3

# 部署到服务器
bash ~/Project/news.techdou.com/scripts/deploy.sh 2026-06-27
```

## deploy.sh

```bash
# 用法
bash scripts/deploy.sh YYYY-MM-DD

# 自动完成：
# 1. 创建服务器目录
# 2. 上传 HTML + 音频
# 3. 同步静态资源 (logo, favicon, pet)
# 4. 设置权限
# 5. 更新 symlink (index.html → 当天)
# 6. 重新生成 archive.html
```

## TTS 质量检查

部署前必查：
- [ ] 播报条数与实际新闻一致
- [ ] 时长 > 120 秒
- [ ] 文件大小 > 2MB
- [ ] 开头有"欢迎收听 TechDaily"

## 错误处理

| 场景 | 处理 |
|------|------|
| RSS 不可达 | 30s 后重试，仍失败 → 部署 no-update.html + 1h 后自动重试 |
| 无今日内容 | 部署 no-update.html |
| TTS 失败 | 重试 3 次（间隔 10s），仍失败 → 只部署 HTML |
| 部署失败 | 保留本地，通知用户 |

## Template Auto-Injection

`assemble.py` 自动注入：
- `<body data-date="YYYY-MM-DD">` — 供 JS 识别当前日期
- `window.TechDailyAudioUrl` — 指向当天音频文件

## 关键教训

| 日期 | 教训 |
|------|------|
| 06-25 | `mmx speech synthesize` 从 stdin 读取会截断 → 必须 `--text-file` |
| 06-25 | RSS 的 `<h2>` 可能变 `<h3>` → 解析器同时匹配 `<h[23]>` |
| 06-25 | RSS 403 → 必须带 User-Agent 头 |
| 06-26 | 音频路径必须用日期目录，不能用顶层 `broadcast.mp3` |
| 06-26 | pipeline HTML 模板必须外置，不能内联在 Python |
| 06-27 | archive.html 日期以目录路径为准，不读 HTML title |

## Cron 配置

```json
{
  "name": "daily-news",
  "schedule": { "kind": "cron", "expr": "0 10 * * *", "tz": "Asia/Shanghai" },
  "payload": { "kind": "agentTurn", "message": "执行每日日报生成流程" },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "openclaw-weixin" },
  "payload": { "timeoutSeconds": 900 }
}
```
