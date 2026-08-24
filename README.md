# 📰 TechDaily

> AI 驱动的每日科技日报 — RSS 抓取 → 自动解析 → TTS 音频播报 → 全自动部署

**线上地址**：[news.techdou.com](https://news.techdou.com)

---

## ✨ 特性

- **全自动流水线**：RSS 抓取 → 解析 → HTML 生成 → TTS 音频 → Git 版本管理 → 服务器部署
- **首页状态机**：凌晨自动切「待更新」页，日报发布后切回当日内容（symlink 驱动，零延迟）
- **报纸式排版**：报刊风格，分类导航 + 术语弹窗 + 图片灯箱 + 阅读进度条
- **TTS 语音播报**：每日生成中文新闻播报音频（本地 CosyVoice3，音色可换）
- **对账哨兵**：概览区与详细区条数强制对账，解析异常立即报警中止，拒绝发布残缺日报
- **往期回顾**：按月归档，支持「最近 7 天」/「全部」筛选
- **容错机制**：RSS 不可用时秒切待更新页，1 小时后自动重试

## 🏗️ 项目结构

```
techdaily/
├── scripts/                    # 构建脚本
│   ├── pipeline.py             # 全自动流水线（主入口）
│   ├── assemble.py             # HTML 组装器
│   ├── deploy.sh               # 部署脚本（手动备用入口）
│   ├── switch-to-pending.sh    # 凌晨 cron：首页切待更新页
│   └── gen-archive.sh          # 归档页生成器
├── templates/                  # HTML 模板
│   ├── template-head.html      # CSS 模板
│   ├── template-tail.html      # JS 模板
│   └── no-update.html          # 待更新页源模板
├── public/                     # 静态网站根目录（部署内容，纳入版本管理）
│   ├── YYYY/MM/DD/             # 每日日报（index.html + audio.mp3）
│   ├── archive.html            # 往期回顾
│   ├── pending.html            # 待更新占位页
│   └── assets/                 # Logo、favicon 等静态资源
├── docs/                       # 参考文档
└── .github/workflows/          # GitHub Actions
```

> `output/`（本地构建产物）、`SKILL.md`（内部运维手册）不入库，见 `.gitignore`。

## 🔄 工作流

```
00:00 凌晨 cron → switch-to-pending.sh → symlink → pending.html（待更新页）

10:00 上午 cron → pipeline.py
    ├─ 1. 抓取 RSS → 解析（概览 + 详细报道）
    ├─ 2. 对账哨兵：两边条数一致才放行
    ├─ 3. assemble.py 组装完整 HTML
    ├─ 4. TTS 合成播报音频（CosyVoice3）
    ├─ 5. 保存到 public/YYYY/MM/DD/
    ├─ 6. git commit + push → 服务器 git pull + 同步
    ├─ 7. symlink → 当日日报上线
    └─ 8. 更新 archive.html

    └─ 若 RSS 失败 → deploy_no_update() → 切回 pending.html，1h 后自动重试
```

### 首页状态机

| 状态 | symlink 指向 | 触发器 |
|------|-------------|--------|
| 🌙 凌晨待更新 | `pending.html` | 凌晨 cron |
| 📰 当日日报 | `YYYY/MM/DD/index.html` | pipeline 部署成功后 |
| ⚠️ RSS 失败 | `pending.html` | `deploy_no_update()` |

## 🚀 快速开始

### 前置要求

- Python 3.10+
- SSH 免密登录到部署服务器
- ffmpeg（音频转码）
- TTS 引擎（本地 CosyVoice3，可选——不可用时仅跳过音频）

### 配置

所有服务器信息通过环境变量注入，**不硬编码在代码中**：

```bash
# 部署目标（必填）
export DEPLOY_USER="your_user"
export DEPLOY_HOST="your_server_ip"
export DEPLOY_SERVER="your_user@your_server_ip"   # deploy.sh 用
export DEPLOY_PATH="/var/www/your-domain"          # deploy.sh 用

# 服务器侧（首次部署需具备）
# - /var/www/<domain>/ 目录
# - git 仓库 clone + sync-from-git.sh 同步脚本
# - Nginx 静态站点配置
```

### 使用

```bash
# 全自动生成当日日报（抓取→解析→音频→HTML→部署）
python3 scripts/pipeline.py

# 指定日期 / 跳过阶段 / 仅解析
python3 scripts/pipeline.py --date 2026-08-24
python3 scripts/pipeline.py --skip-tts --skip-deploy
python3 scripts/pipeline.py --parse-only

# 手动部署（pipeline 之外重新上线某天）
bash scripts/deploy.sh 2026-08-24

# 重新生成归档页
bash scripts/gen-archive.sh
```

## 🛡️ 可靠性设计

| 机制 | 说明 |
|------|------|
| 对账哨兵 | 概览列出的每条新闻必须有对应正文，缺一条 → 抛错 + 写报警文件，**禁止静默发布残缺日报** |
| 无链接新闻兼容 | 解析正则允许新闻无超链接（源站偶尔缺），渲染为纯文本标题 |
| 正则双层防御 | 负向前瞻防跨标签吞内容；关键正则带 CRITICAL 注释，防止重写时回退 |
| 音频缓存穿透 | 音频 URL 带 `?v=<mtime>` 后缀，同日重生成音频不会被 CDN 24h 缓存咬住 |
| RSS 容错 | 抓取失败 → 切待更新页 → 1h 后自动重试 → 报警文件通知 |

## 📁 环境变量一览

| 变量 | 必填 | 说明 |
|------|:----:|------|
| `DEPLOY_USER` / `DEPLOY_HOST` | ✅ | SSH 部署目标（pipeline.py） |
| `DEPLOY_SERVER` / `DEPLOY_PATH` | ✅ | `user@ip` 与站点根目录（deploy.sh） |
| `NEWS_TTS_VOICE` | ❌ | TTS 音色（默认 `dou`） |
| `SERVER_USER` / `SERVER_HOST` | ❌ | 覆盖部署目标的别名 |

> ⚠️ **安全原则**：服务器 IP、SSH 凭证、API Key 等一律走环境变量或本地 `.env`（已 gitignore），绝不提交入库。

## 📜 License

MIT © TechDou
