"""API路由"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from .bilibili import fetch_video_info
from .scheduler import collect_one, reschedule, get_current_interval
from .store import DataStore

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# 允许的采集间隔选项（秒）
ALLOWED_INTERVALS = [10, 15, 30, 60, 120, 300]


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 展示监控列表"""
    bvids = DataStore.get_monitored_bvids()
    monitors = []
    for bvid in bvids:
        info = DataStore.get_info(bvid)
        monitors.append({"bvid": bvid, "info": info})
    config = DataStore.get_config()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "monitors": monitors,
            "interval": config.get("interval", 30),
            "allowed_intervals": ALLOWED_INTERVALS,
        },
    )


@router.post("/api/monitor")
async def add_monitor(bvid: str):
    """添加监控 - 输入BV号开始监控"""
    # 先采集一次数据验证BV号有效
    ok = await collect_one(bvid)
    if not ok:
        return {"success": False, "msg": "BV号无效或网络错误"}
    DataStore.add_monitor(bvid)
    info = DataStore.get_info(bvid)
    return {"success": True, "msg": "已添加监控", "info": info}


@router.delete("/api/monitor")
async def remove_monitor(bvid: str):
    """移除监控"""
    DataStore.remove_monitor(bvid)
    return {"success": True, "msg": "已移除监控"}


@router.get("/api/stats/{bvid}")
async def get_stats(bvid: str):
    """获取视频统计数据（供趋势图使用）"""
    stats = DataStore.get_stats(bvid)
    info = DataStore.get_info(bvid)
    return {"info": info, "stats": stats}


@router.get("/chart/{bvid}", response_class=HTMLResponse)
async def chart_page(request: Request, bvid: str):
    """趋势图页面"""
    info = DataStore.get_info(bvid)
    config = DataStore.get_config()
    return templates.TemplateResponse(
        request=request,
        name="chart.html",
        context={"bvid": bvid, "info": info, "interval": config.get("interval", 30)},
    )


# ── 配置 API ──

@router.get("/api/config")
async def get_config():
    """获取当前配置"""
    config = DataStore.get_config()
    config["interval"] = get_current_interval()
    return config


class IntervalBody(BaseModel):
    interval: int


@router.put("/api/config/interval")
async def set_interval(body: IntervalBody):
    """修改采集间隔（秒）"""
    seconds = body.interval
    if seconds not in ALLOWED_INTERVALS:
        return {"success": False, "msg": f"间隔必须是以下值之一: {ALLOWED_INTERVALS}"}
    if seconds < 10:
        return {"success": False, "msg": "间隔不能小于10秒"}

    # 持久化配置
    DataStore.set_config({"interval": seconds})
    # 动态修改调度器
    reschedule(seconds)

    return {"success": True, "msg": f"采集间隔已修改为 {seconds} 秒", "interval": seconds}
