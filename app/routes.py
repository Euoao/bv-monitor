"""API路由"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from .bilibili import fetch_video_info
from .scheduler import (
    collect_one, add_video_job, remove_video_job,
    reschedule_video, reschedule_default_videos,
)
from .store import DataStore

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _format_num(value) -> str:
    """将数字格式化为可读文本（万/亿）"""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return f"{n:,}"


templates.env.filters["format_num"] = _format_num

router = APIRouter()

# 允许的采集间隔选项（秒）
ALLOWED_INTERVALS = [10, 15, 30, 60, 120, 300]


def _fmt_interval(sec: int) -> str:
    """将秒数格式化为可读文本"""
    if sec < 60:
        return f"{sec}秒"
    return f"{sec // 60}分钟"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 展示监控列表"""
    bvids = DataStore.get_monitored_bvids()
    config = DataStore.get_config()
    global_interval = config.get("interval", 30)

    monitors = []
    for bvid in bvids:
        info = DataStore.get_info(bvid)
        video_interval = DataStore.get_video_interval(bvid)
        effective = DataStore.get_effective_interval(bvid)
        latest_stat = DataStore.get_latest_stat(bvid)
        monitors.append({
            "bvid": bvid,
            "info": info,
            "latest_stat": latest_stat,
            "effective_interval": effective,
            "effective_label": _fmt_interval(effective),
            "is_custom": video_interval is not None,
        })

    interval_options = [{"value": s, "label": _fmt_interval(s)} for s in ALLOWED_INTERVALS]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "monitors": monitors,
            "interval": global_interval,
            "interval_label": _fmt_interval(global_interval),
            "interval_options": interval_options,
        },
    )


@router.post("/api/monitor")
async def add_monitor(bvid: str):
    """添加监控 - 输入BV号开始监控"""
    ok = await collect_one(bvid)
    if not ok:
        return {"success": False, "msg": "BV号无效或网络错误"}
    DataStore.add_monitor(bvid)
    add_video_job(bvid)
    info = DataStore.get_info(bvid)
    return {"success": True, "msg": "已添加监控", "info": info}


@router.delete("/api/monitor")
async def remove_monitor(bvid: str):
    """移除监控"""
    DataStore.remove_monitor(bvid)
    remove_video_job(bvid)
    return {"success": True, "msg": "已移除监控"}


@router.get("/api/stats/{bvid}")
async def get_stats(bvid: str, limit: int | None = Query(None, ge=1, description="最多返回最近N条")):
    """获取视频统计数据（供趋势图使用）"""
    stats = DataStore.get_stats(bvid, limit=limit)
    info = DataStore.get_info(bvid)
    return {"info": info, "stats": stats}


@router.get("/chart/{bvid}", response_class=HTMLResponse)
async def chart_page(request: Request, bvid: str):
    """趋势图页面"""
    info = DataStore.get_info(bvid)
    effective_interval = DataStore.get_effective_interval(bvid)
    return templates.TemplateResponse(
        request=request,
        name="chart.html",
        context={"bvid": bvid, "info": info, "interval": effective_interval},
    )


# ── 全局配置 API ──

@router.get("/api/config")
async def get_config():
    """获取全局配置"""
    return DataStore.get_config()


class IntervalBody(BaseModel):
    interval: int


@router.put("/api/config/interval")
async def set_interval(body: IntervalBody):
    """修改全局采集间隔（秒）"""
    seconds = body.interval
    if seconds not in ALLOWED_INTERVALS:
        return {"success": False, "msg": f"间隔必须是以下值之一: {ALLOWED_INTERVALS}"}

    DataStore.set_config({"interval": seconds})
    reschedule_default_videos(seconds)
    return {"success": True, "msg": f"全局采集间隔已修改为 {seconds} 秒", "interval": seconds}


# ── 单视频间隔 API ──

class VideoIntervalBody(BaseModel):
    interval: int | None = None


@router.put("/api/video/{bvid}/interval")
async def set_video_interval(bvid: str, body: VideoIntervalBody):
    """设置单视频采集间隔，interval=null 表示跟随全局"""
    seconds = body.interval
    if seconds is not None and seconds not in ALLOWED_INTERVALS:
        return {"success": False, "msg": f"间隔必须是以下值之一: {ALLOWED_INTERVALS}"}

    DataStore.set_video_interval(bvid, seconds)
    effective = DataStore.get_effective_interval(bvid)
    reschedule_video(bvid, effective)

    return {
        "success": True,
        "msg": f"已设为 {_fmt_interval(effective)}" if seconds else f"已跟随全局（{_fmt_interval(effective)}）",
        "effective_interval": effective,
        "effective_label": _fmt_interval(effective),
        "is_custom": seconds is not None,
    }
