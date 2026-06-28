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
                        ┌─ 00:00 agent cron ─→ switch-to-pending.sh ─→ symlink→pending.html
                        │
RSS (daily.juya.uk)     │
  ↓ fetch + parse       │
pipeline.py ────────────┘─ 10:00 agent cron
  ↓ assemble.py (template-head + template-tail)
完整 HTML (~140KB)
  ↓ + TTS 音频 (mmx speech synthesize)
deploy_site() → public/YYYY/MM/DD/ → git push → 服务器 git pull
  ↓ sudo ln -sfn YYYY/MM/DD/index.html  /var/www/news.techdou.com/index.html
  ↓
gen-archive.sh → 更新 archive.html
```

**部署双轨说明**：`deploy_site()`（pipeline.py，cron 用）与 `deploy.sh`（手动备用）是两套等价实现，都做「git push + ssh sync + ln -sfn + gen-archive」。**以 pipeline.py 为准**，deploy.sh 仅在手动触发时使用。

## 项目结构

```
~/Project/news.techdou.com/
├── SKILL.md                 # 本文件
├── README.md
├── scripts/
│   ├── pipeline.py          # 全自动 Pipeline（主入口）
│   ├── assemble.py          # HTML 组装器（template-head + content + template-tail）
│   ├── deploy.sh            # 部署到服务器（手动备用入口）
│   ├── switch-to-pending.sh # 凌晨 cron 调用：根 / 切到 pending 页
│   └── gen-archive.sh       # 生成 archive.html
├── templates/
│   ├── template-head.html   # CSS 模板（68KB，固定）
│   ├── template-tail.html   # JS 模板（37KB，固定）
│   └── no-update.html       # 待更新页源模板（复制为 public/pending.html）
├── docs/
│   ├── content-schema.md    # content.json 字段说明
│   └── rss-structure.md     # RSS 结构参考
└── public/                  # 部署到服务器的静态文件
    ├── 2026/06/DD/          # 每日日报 (index.html + audio.mp3)
    ├── archive.html         # 往期回顾
    ├── pending.html         # 待更新占位页（凌晨/RSS失败时根 / 指向它）
    ├── pet.html / pet.js    # 吉祥物
    └── assets/              # logo、favicon、宠物素材
```

## 首页状态机

根 `/` 显示什么，由服务器 `/var/www/news.techdou.com/index.html` 这个 **symlink** 决定（nginx 仅做静态映射）。三种状态靠改 symlink 指向切换：

| 状态 | symlink 指向 | 触发器 |
|------|-------------|--------|
| 🌙 凌晨待更新（00:00–日报发布前） | `pending.html` | 凌晨 agent cron 调 `switch-to-pending.sh` |
| 📰 当日日报（发布后） | `YYYY/MM/DD/index.html` | pipeline.py `deploy_site()` 成功后 `ln -sfn` |
| ⚠️ RSS 失败/无今日内容 | `pending.html` | pipeline.py `deploy_no_update()` |

> 设计要点：`pending.html` 是常驻在 `public/` 根目录的占位页（内容由 `templates/no-update.html` 复制），随 git 同步到服务器。切换只需一条 `ln -sfn`，**占位页不再复制进日期目录**——避免被 `gen-archive.sh` 误收为「正常日报」。
>
> 每日循环：00:00 切 pending → 10:00 pipeline 生成日报并切到当日 → 次日 00:00 又切 pending，周而复始。

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
# 部署指定日期（手动备用入口，等价于 pipeline 的 deploy_site）
bash ~/Project/news.techdou.com/scripts/deploy.sh 2026-06-27

# 重新生成归档页
bash ~/Project/news.techdou.com/scripts/gen-archive.sh

# 手动切首页到待更新页（调试用，等价于凌晨 cron）
bash ~/Project/news.techdou.com/scripts/switch-to-pending.sh
```

> 修改了 `templates/no-update.html` 后，记得 `cp` 一份到 `public/pending.html`，否则线上待更新页不会更新。

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
| RSS 不可达 | `deploy_no_update()` 切 symlink → pending.html + 1h 后自动重试 |
| 无今日内容 | `deploy_no_update()` 切 symlink → pending.html |
| TTS 失败 | 重试 3 次（间隔 10s），仍失败 → 检查服务器已有音频 → 只部署 HTML |
| 部署失败 | 保留本地，通知用户 |

## Cron 配置

两个 agent cron 协作，构成「凌晨切 pending → 上午发日报」的每日循环：

```json
// ① 凌晨：切换首页到待更新页
{
  "name": "daily-news-pending",
  "schedule": { "kind": "cron", "expr": "0 0 * * *", "tz": "Asia/Shanghai" },
  "payload": { "kind": "agentTurn", "message": "运行 bash ~/Project/news.techdou.com/scripts/switch-to-pending.sh 切换首页到待更新状态" },
  "sessionTarget": "isolated"
}

// ② 上午：生成并发布当日日报（成功后自动切回报当日）
{
  "name": "daily-news",
  "schedule": { "kind": "cron", "expr": "0 10 * * *", "tz": "Asia/Shanghai" },
  "payload": { "kind": "agentTurn", "message": "执行每日日报生成流程，运行 pipeline.py" },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "openclaw-weixin" }
}
```

> 凌晨 cron 已配好基建（脚本就绪），agent cron 任务由用户自行在 agent 平台注册。
> 若当日 10:00 pipeline 走 RSS 失败分支，symlink 会被 `deploy_no_update()` 切到 pending，无需凌晨 cron 介入。

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
| 06-28 | 占位页改用常驻 `public/pending.html` + symlink 切换，**不要**复制进日期目录——否则 gen-archive 误收占位日期为「正常日报」 |
| 06-28 | 首页状态靠服务器 `/var/www/.../index.html` symlink 决定，凌晨 cron 切 pending、pipeline 成功切当日，是「状态机」而非「覆盖文件」 |
