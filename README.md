# BV Monitor

B 站视频数据实时监控工具。输入视频 BV 号，自动定时采集播放量、点赞、投币、收藏等指标，以趋势折线图的形式展示数据变化，部署在本地运行。

## 项目简介

本项目通过调用 B 站公开接口（`api.bilibili.com/x/web-interface/view`），定时获取指定视频的统计数据，并将每次采集结果持久化到本地 JSON 文件中。后端基于 FastAPI 提供 Web 服务与数据接口，前端使用 Chart.js 绘制趋势折线图，实现对视频各项数据变化的可视化追踪。

核心流程：

```
输入 BV 号 → 验证并首次采集 → 定时任务每 30 秒采集 → 数据持久化 → 前端图表展示趋势
```

## 功能特性

- 支持通过 BV 号添加 / 移除视频监控
- 后台定时采集（默认间隔 60 秒）
- 趋势折线图展示播放量、点赞、投币、收藏等指标
- 支持同时监控多个视频
- 数据以 JSON 文件形式本地持久化，重启后自动延续

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## 快速开始

**安装依赖：**

```bash
uv sync
```

**启动服务：**

```bash
uv run python main.py
```

启动后在浏览器访问 http://localhost:8000 即可使用。

## 使用方式

1. 在首页输入视频 BV 号（例如 `BV1xx411c7mD`），点击「开始监控」
2. 系统会验证 BV 号有效性，验证通过后立即执行一次数据采集
3. 点击「查看趋势」进入图表页面，查看播放量及互动数据的变化曲线
4. 后台每 30 秒自动采集一次，图表页面同步自动刷新

## 运行机制

### 启动行为

程序启动后会执行以下操作：

1. 在 `0.0.0.0:8000` 启动 Web 服务
2. 启动后台定时任务（APScheduler），每 30 秒对所有已监控的 BV 号调用 B 站 API 采集数据
3. 采集结果追加写入 `data/` 目录下对应的 JSON 文件

终端会输出如下日志表示启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 运行方式

程序默认以**前台方式**运行，占用当前终端窗口。关闭终端会导致服务停止。

如需后台运行：

```bash
nohup uv run python main.py > bv_monitor.log 2>&1 &
```

### 停止服务

- 前台运行：终端中按 `Ctrl + C`
- 后台运行：

```bash
ps aux | grep main.py
kill <PID>
```

### 数据存储

采集数据保存在项目根目录的 `data/` 文件夹中（首次运行时自动创建）：

| 文件 | 说明 |
| --- | --- |
| `data/_monitors.json` | 当前监控的 BV 号列表 |
| `data/<BV号>.json` | 对应视频的基本信息与全部历史采集数据 |

- 数据格式为 JSON，可直接查看或二次处理
- 服务停止后数据不会丢失，下次启动会在已有数据上继续追加
- `data/` 已加入 `.gitignore`，不会提交到版本库

## 注意事项

- 开发模式下默认开启热重载（`reload=True`），修改代码后服务会自动重启
- B 站接口存在访问频率限制，同时监控的视频数量建议不超过 20 个
- 默认端口为 `8000`，可在 `main.py` 中修改 `port` 参数

## 项目结构

```
bv_monitor/
├── main.py                # 入口文件，启动 uvicorn 服务
├── pyproject.toml         # 项目配置与依赖声明
├── app/
│   ├── __init__.py        # 应用工厂，组装路由与生命周期
│   ├── bilibili.py        # B 站 API 封装（视频信息 / 统计数据）
│   ├── store.py           # 数据持久化（JSON 文件读写）
│   ├── scheduler.py       # 定时采集任务（APScheduler）
│   └── routes.py          # HTTP 路由与页面渲染
├── templates/
│   ├── index.html         # 首页（监控管理）
│   └── chart.html         # 趋势图页面
└── data/                  # 运行时生成，存放采集数据
```

## 技术栈

| 组件 | 用途 |
| --- | --- |
| FastAPI | Web 框架与 API 服务 |
| httpx | 异步 HTTP 客户端 |
| APScheduler | 后台定时任务调度 |
| Jinja2 | HTML 模板渲染 |
| Chart.js | 前端趋势图表 |
| uv | Python 包管理与虚拟环境 |
