# BV Monitor - B站视频数据实时监控

输入 BV 号，实时监控 B 站视频的播放量、点赞、投币、收藏等数据，并生成趋势图。

## 做了什么

通过 B 站公开 API（`api.bilibili.com/x/web-interface/view`）定时抓取指定视频的统计数据，将每次采集的播放量、点赞、投币、收藏、分享、弹幕数记录下来，存储为本地 JSON 文件。后端用 FastAPI 提供 Web 服务和数据接口，前端用 Chart.js 将历史数据绘制成趋势折线图，实现对视频数据变化的可视化追踪。

整体流程：**输入 BV 号 → 后台每 60 秒采集一次 → 数据写入本地 → 前端图表展示趋势**。

## 功能

- 输入 BV 号即可添加监控
- 每 60 秒自动采集一次数据
- Chart.js 趋势图展示播放量、点赞、投币、收藏变化
- 支持同时监控多个视频
- 数据本地 JSON 文件持久化存储

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动服务

```bash
uv run python main.py
```

服务启动后访问 **http://localhost:8000**

### 3. 使用

1. 在首页输入框中输入视频的 **BV 号**（例如 `BV1xx411c7mD`）
2. 点击 **开始监控**，系统会验证 BV 号并立即采集一次数据
3. 点击 **查看趋势** 进入趋势图页面，查看播放量和互动数据的实时变化曲线
4. 系统每 60 秒自动采集数据，趋势图页面也会每 60 秒自动刷新

## 项目结构

```
bv_monitor/
├── main.py                # 主入口，启动 uvicorn 服务
├── pyproject.toml         # 项目配置与依赖
├── app/
│   ├── __init__.py        # FastAPI 应用工厂
│   ├── bilibili.py        # B站 API 封装
│   ├── store.py           # JSON 文件数据存储
│   ├── scheduler.py       # APScheduler 定时采集
│   └── routes.py          # API 路由与页面渲染
├── templates/
│   ├── index.html         # 首页（输入 BV 号 + 监控列表）
│   └── chart.html         # 趋势图页面
└── data/                  # 运行时生成，存放采集数据（已 gitignore）
```

## 技术栈

- **FastAPI** - Web 框架
- **httpx** - 异步 HTTP 请求
- **APScheduler** - 定时任务调度
- **Jinja2** - 模板渲染
- **Chart.js** - 前端趋势图表
- **uv** - 包管理
