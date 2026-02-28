"""API路由"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .bilibili import fetch_video_info
from .scheduler import collect_one
from .store import DataStore

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 展示监控列表"""
    bvids = DataStore.get_monitored_bvids()
    monitors = []
    for bvid in bvids:
        info = DataStore.get_info(bvid)
        monitors.append({"bvid": bvid, "info": info})
    return templates.TemplateResponse(
        request=request, name="index.html", context={"monitors": monitors}
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
    return templates.TemplateResponse(
        request=request, name="chart.html", context={"bvid": bvid, "info": info}
    )
