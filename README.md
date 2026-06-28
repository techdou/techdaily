# 📰 TechDaily

> AI 驱动的每日科技日报 — RSS → AI 摘要 → TTS 音频 → 自动部署

**线上地址**：[news.techdou.com](https://news.techdou.com)

---

## ✨ 特性

- **全自动流水线**：RSS 抓取 → 解析 → HTML 生成 → TTS 音频 → GitHub 版本管理 → 服务器部署
- **首页状态机**：凌晨自动切「待更新」页，日报发布后切回当日内容（symlink 驱动，零延迟）
- **报纸式排版**：精仿报刊风格，分类导航 + 术语弹窗 + 图片灯箱 + 阅读进度
- **TTS 语音播报**：每日生成中文新闻播报音频（MiniMax Podcast_girl 音色）
- **往期回顾**：按月归档，支持「最近 7 天」/「全部」筛选，渐进增强 + 无障碍优化
- **吉祥物**：金豆宠物互动（桌面端）
- **容错机制**：RSS 不可用时秒切待更新页，1 小时后自动重试

---

## 🏗️ 项目结构

```
techdaily/
├── scripts/                    # 构建脚本
│   ├── pipeline.py             # 全自动流水线（主入口）
│   ├── assemble.py             # HTML 组装器（template-head + content + template-tail）
│   ├── deploy.sh               # 部署脚本（手动备用入口）
│   ├── switch-to-pending.sh    # 凌晨 cron 调用：首页切到待更新页
│   └── gen-archive.sh          # 归档页生成器（生成 → 部署 → 同步回仓库）
├── templates/                  # HTML 模板
│   ├── template-head.html      # CSS 模板（68KB）
│   ├── template-tail.html      # JS 模板（37KB）
│   └── no-update.html          # 待更新页源模板
├── public/                     # 静态网站根目录
│   ├── 2026/06/DD/             # 每日日报（index.html + audio.mp3）
│   ├── archive.html            # 往期回顾（由 gen-archive.sh 生成）
│   ├── pending.html            # 待更新占位页（凌晨/RSS失败时首页指向它）
│   ├── assets/                 # Logo、favicon、宠物素材
│   │   └── logo/favicon.svg
│   └── pet.html / pet.js       # 吉祥物
├── docs/                       # 参考文档
│   ├── content-schema.md       # 数据结构说明
│   └── rss-structure.md        # RSS 源结构
├── SKILL.md                    # OpenClaw Skill 定义
├── LICENSE                     # MIT License
└── README.md                   # 本文件
```

---

## 🎛️ 首页状态机

根 `/` 显示内容由服务器 `/var/www/news.techdou.com/index.html` 这个 **symlink** 决定（nginx 仅做静态映射）。两个 cron 协作完成每日状态切换：

| 状态 | symlink 指向 | 触发器 |
|------|-------------|--------|
| 🌙 凌晨待更新（00:00 – 日报发布前） | `pending.html` | 凌晨 agent cron 调 `switch-to-pending.sh` |
| 📰 当日日报（发布后） | `YYYY/MM/DD/index.html` | `pipeline.py` 的 `deploy_site()` 成功后 `ln -sfn` |
| ⚠️ RSS 失败 / 无今日内容 | `pending.html` | `pipeline.py` 的 `deploy_no_update()` |

> 设计要点：`pending.html` 是常驻在 `public/` 根目录的占位页（内容源自 `templates/no-update.html`），随 git 同步到服务器。切换只需一条 `ln -sfn`，**占位页不再复制进日期目录**——避免被归档页生成器误收为「正常日报」。

---

## 🔄 工作流

```
00:00 凌晨 cron → switch-to-pending.sh → symlink → pending.html（待更新页）
                                                  │
10:00 上午 cron → pipeline.py                   │
    ├─ 1. 抓取 RSS（daily.juya.uk）→ 解析新闻    │
    ├─ 2. clean_rss_artifacts() 清理 RSS 模板变量 │
    ├─ 3. assemble.py 组装完整 HTML               │
    ├─ 4. TTS 合成播报音频（MiniMax）             │
    ├─ 5. 保存到 public/YYYY/MM/DD/              │
    ├─ 6. git commit + push → 服务器 git pull      │
    ├─ 7. symlink → YYYY/MM/DD/index.html ◀──────┘ 当日日报上线
    └─ 8. 更新 archive.html + 微信通知

    └─ 若 RSS 失败 → deploy_no_update() → symlink → pending.html（保持待更新）
```

---

## 🚀 部署

### 自动部署（Cron）

两个 agent cron 协作，构成「凌晨切 pending → 上午发日报」的每日循环（详细配置见 `SKILL.md`）：

- **00:00** — `switch-to-pending.sh`：首页切到待更新状态
- **10:00** — `pipeline.py`：生成当日日报并切回首页

### 手动部署

```bash
# 全自动（推荐）
python3 scripts/pipeline.py --date 2026-06-27

# 仅部署已有文件（手动备用入口，等价于 pipeline 的 deploy_site）
bash scripts/deploy.sh 2026-06-27

# 重新生成归档页（生成 → 部署到服务器 → 同步回 public/archive.html）
bash scripts/gen-archive.sh

# 手动切首页到待更新页（调试用，等价于凌晨 cron）
bash scripts/switch-to-pending.sh
```

> **注意**：修改了 `templates/no-update.html` 后，记得 `cp` 一份到 `public/pending.html`，否则线上待更新页不会更新。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_USER` | `ubuntu` | SSH 用户 |
| `SERVER_HOST` | `43.153.24.30` | 服务器地址 |

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 内容源 | RSS（daily.juya.uk） |
| HTML 模板 | 纯 HTML/CSS/JS，无框架 |
| TTS | MiniMax Speech（Podcast_girl） |
| 版本管理 | Git + GitHub |
| 部署 | Server git pull + rsync → Nginx |
| 自动化 | OpenClaw Cron |

---

## 📜 License

MIT © [TechDou](https://github.com/DouXiulu)
