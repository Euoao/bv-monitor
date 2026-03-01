# BV Monitor

B 站视频数据实时监控工具。输入视频 BV 号，自动定时采集播放量、点赞、投币、收藏等指标，以趋势折线图展示数据变化，部署在本地运行。

## 功能特性

- 通过 BV 号添加 / 移除视频监控，支持同时监控多个视频
- 后台定时采集，支持全局默认间隔和单视频独立间隔设置
- 可选间隔：10 秒、15 秒、30 秒（默认）、1 分钟、2 分钟、5 分钟
- 趋势折线图展示播放量、点赞、投币、收藏，各指标独立纵轴
- 图表支持拖拽选区缩放、重置视图，纵轴自适应可见数据范围
- 数据悬浮提示显示精确数值
- 视频封面展示，标题可跳转至 B 站视频页
- 数据本地持久化，重启后自动延续采集
- 统计数据采用 JSONL 追加写入，高效不重写

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- Linux / macOS / Windows 均可运行（systemd 部署仅限 Linux）

## 快速开始

### Linux / macOS

```bash
# 1. 克隆项目
git clone <repo-url> && cd bv_monitor

# 2. 安装依赖
uv sync

# 3. 启动服务
uv run python main.py
```

### Windows

```powershell
# 1. 安装 uv（如尚未安装）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 克隆项目
git clone <repo-url>
cd bv_monitor

# 3. 安装依赖
uv sync

# 4. 启动服务
uv run python main.py
```

启动后浏览器访问 **http://localhost:8000** 即可使用。

## 使用方式

1. 在首页输入视频 BV 号（如 `BV1xx411c7mD`），点击「开始监控」
2. 系统验证 BV 号有效性后立即执行首次采集
3. 点击视频卡片上的「📈 查看趋势」进入图表页，查看各项数据的变化曲线
4. 后台按设定间隔自动采集，图表页同步自动刷新

### 采集间隔配置

- **全局间隔**：首页输入框右侧的 ⚙️ 图标，点击弹出菜单选择
- **单视频间隔**：视频卡片上的 ⏱ 标签，点击弹出菜单选择；设为「跟随全局」则使用全局间隔

## 部署

### 命令行参数

```bash
uv run python main.py [-p PORT] [--dev]
```

| 参数 | 说明 |
| --- | --- |
| `-p` / `--port` | 监听端口，默认 `8000` |
| `--dev` | 开发模式，启用热重载（内存翻倍，仅开发时使用） |

### Linux 部署

#### 前台运行（开发 / 调试）

```bash
uv run python main.py
```

- 占用当前终端，关闭终端则服务停止
- 按 `Ctrl + C` 停止

#### systemd 服务（推荐生产部署）

**安装并启动服务：**

```bash
sudo bash scripts/install.sh        # 默认端口 8000
sudo bash scripts/install.sh 9000   # 指定端口
```

脚本会自动检测项目路径和运行用户，生成 systemd service 文件，启用开机自启并立即启动服务。

**常用管理命令：**

```bash
# 查看状态
systemctl status bv-monitor

# 查看实时日志
journalctl -u bv-monitor -f

# 重启服务
sudo systemctl restart bv-monitor

# 停止服务
sudo systemctl stop bv-monitor
```

**卸载服务：**

```bash
sudo bash scripts/uninstall.sh
```

> 卸载仅移除 systemd 服务配置，`data/` 目录中的采集数据不会被删除。

#### 后台进程

```bash
nohup uv run python main.py > data/bv_monitor.log 2>&1 &
```

停止时需手动查找并终止进程：

```bash
ps aux | grep bv-monitor
kill <PID>
```

### Windows 部署

#### 前台运行

```powershell
uv run python main.py
```

- 窗口保持打开，关闭窗口则服务停止
- 按 `Ctrl + C` 停止

#### 后台运行（隐藏窗口）

在项目目录下执行：

```powershell
Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run","python","main.py" -RedirectStandardOutput "data\bv_monitor.log" -RedirectStandardError "data\bv_monitor_err.log"
```

日志文件保存在 `data/` 目录中。

> `setproctitle` 在 Windows 上仅改变控制台窗口标题，进程名仍为 `python`，无法通过进程名查找。建议通过监听端口定位进程：

```powershell
# 查找占用 8000 端口的进程 PID
netstat -ano | findstr :8000

# 终止进程（替换 <PID> 为上一步查到的数字）
taskkill /PID <PID> /F
```

#### 开机自启（计划任务）

通过 Windows 任务计划程序实现开机自启：

```powershell
# 创建计划任务（以当前用户身份，开机时启动）
$action = New-ScheduledTaskAction `
    -Execute "C:\Users\<你的用户名>\.local\bin\uv.exe" `
    -Argument "run python main.py" `
    -WorkingDirectory "C:\path\to\bv_monitor"

$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName "BVMonitor" -Action $action -Trigger $trigger -Settings $settings
```

管理计划任务：

```powershell
# 查看状态
Get-ScheduledTask -TaskName "BVMonitor"

# 手动启动
Start-ScheduledTask -TaskName "BVMonitor"

# 停止
Stop-ScheduledTask -TaskName "BVMonitor"

# 删除
Unregister-ScheduledTask -TaskName "BVMonitor" -Confirm:$false
```

> 也可以通过图形界面操作：`Win + R` → 输入 `taskschd.msc` → 找到 `BVMonitor` 任务进行管理。

## 项目结构

```
bv_monitor/
├── main.py                  # 入口文件，启动 uvicorn 服务
├── pyproject.toml            # 项目元信息与依赖声明
├── uv.lock                  # uv 锁定文件，确保依赖版本一致
├── .gitignore                # Git 忽略规则
├── README.md                 # 项目文档
│
├── app/                      # 后端应用代码
│   ├── __init__.py           # 应用工厂：创建 FastAPI 实例，组装路由与生命周期
│   ├── bilibili.py           # B 站 API 封装：获取视频信息与统计数据
│   ├── store.py              # 数据持久化：JSON 元信息 + JSONL 统计数据
│   ├── scheduler.py          # 定时采集：APScheduler 管理每个视频的独立采集任务
│   └── routes.py             # HTTP 路由：页面渲染与 RESTful API
│
├── templates/                # Jinja2 HTML 模板
│   ├── index.html            # 首页：监控管理、添加/移除视频、间隔设置
│   └── chart.html            # 趋势图页：Chart.js 折线图、拖拽缩放
│
├── scripts/                  # 运维脚本
│   ├── install.sh            # 安装 systemd 服务（开机自启）
│   └── uninstall.sh          # 卸载 systemd 服务
│
├── static/                   # 静态资源目录（预留）
│
└── data/                     # 运行时数据（自动创建，已 gitignore）
    ├── _config.json           # 全局配置（采集间隔等）
    ├── _monitors.json         # 当前监控的 BV 号列表
    ├── <BV号>.json            # 视频元信息（标题、封面、UP主等）
    └── <BV号>_stats.jsonl     # 统计数据（每行一条 JSON，追加写入）
```

### 各模块说明

| 模块 | 职责 |
| --- | --- |
| `main.py` | 程序入口，调用 `create_app()` 创建应用并启动 uvicorn |
| `app/__init__.py` | 应用工厂，注册路由、挂载静态文件、管理生命周期（启动/关闭调度器） |
| `app/bilibili.py` | 封装 B 站 Web API，提供 `fetch_video_info` 和 `fetch_video_stat` 两个异步函数 |
| `app/store.py` | 数据存储层，元信息用 JSON 全量读写，统计数据用 JSONL 追加写入（O(1)），含旧格式自动迁移 |
| `app/scheduler.py` | 基于 APScheduler 的定时采集，每个视频一个独立 Job，支持动态调整间隔 |
| `app/routes.py` | FastAPI 路由，包含首页、图表页渲染以及监控管理、配置、统计数据的 RESTful API |

## 数据存储

采集数据保存在 `data/` 目录（首次运行时自动创建，已加入 `.gitignore`）：

| 文件 | 格式 | 说明 |
| --- | --- | --- |
| `_config.json` | JSON | 全局配置，如默认采集间隔 |
| `_monitors.json` | JSON | 当前监控的 BV 号数组 |
| `<BV号>.json` | JSON | 视频元信息（标题、封面、UP 主等）及可选的独立采集间隔 |
| `<BV号>_stats.jsonl` | JSONL | 统计数据，每行一条 JSON 记录（播放量、点赞等 + 时间戳） |

**JSONL 格式示例**（每行一条）：

```json
{"bvid": "BV1xx411c7mD", "view": 1234567, "like": 45678, "coin": 12345, "favorite": 6789, "share": 1234, "danmaku": 5678, "reply": 2345, "timestamp": "2026-03-01 12:00:00"}
```

- 统计数据采用追加写入（`append`），不会重写整个文件
- 服务停止后数据不丢失，重启后自动继续采集
- 数据可直接用文本编辑器查看或用脚本二次处理

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 首页 |
| `GET` | `/chart/{bvid}` | 趋势图页面 |
| `POST` | `/api/monitor?bvid=BVxxx` | 添加监控 |
| `DELETE` | `/api/monitor?bvid=BVxxx` | 移除监控 |
| `GET` | `/api/stats/{bvid}` | 获取视频统计数据 |
| `GET` | `/api/config` | 获取全局配置 |
| `PUT` | `/api/config/interval` | 修改全局采集间隔 |
| `PUT` | `/api/video/{bvid}/interval` | 修改单视频采集间隔 |

## 技术栈

| 组件 | 用途 |
| --- | --- |
| [FastAPI](https://fastapi.tiangolo.com/) | Web 框架与 API 服务 |
| [uvicorn](https://www.uvicorn.org/) | ASGI 服务器 |
| [httpx](https://www.python-httpx.org/) | 异步 HTTP 客户端 |
| [APScheduler](https://apscheduler.readthedocs.io/) | 后台定时任务调度 |
| [Jinja2](https://jinja.palletsprojects.com/) | HTML 模板渲染 |
| [Chart.js](https://www.chartjs.org/) | 前端趋势图表 |
| [chartjs-plugin-zoom](https://www.chartjs.org/chartjs-plugin-zoom/) | 图表拖拽缩放 |
| [uv](https://docs.astral.sh/uv/) | Python 包管理与虚拟环境 |

## 注意事项

- B 站接口存在访问频率限制，同时监控的视频数量建议不超过 20 个
- 采集间隔过短（如 10 秒）可能触发限流，建议根据监控数量适当调大
- 默认端口 `8000`，通过 `-p` 参数修改：`uv run python main.py -p 9000`
- 默认绑定 `127.0.0.1`（仅本机访问），如需局域网访问需修改 `main.py` 中 `host` 参数
- 开发模式（`--dev`）开启热重载，内存占用翻倍，生产环境勿用
