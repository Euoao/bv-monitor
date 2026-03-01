"""定时采集模块 - 基于 AsyncIO 调度器

使用 AsyncIOScheduler 替代 BackgroundScheduler:
- 与 FastAPI 共享事件循环，无需额外线程池（省 ~10MB）
- 采集任务直接以协程运行，不再为每次采集创建/销毁事件循环
- 可与共享 httpx 客户端协同，复用连接池
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .bilibili import fetch_video_stat, fetch_video_info
from .store import DataStore

scheduler = AsyncIOScheduler()


def _job_id(bvid: str) -> str:
    return f"collect_{bvid}"


async def _collect_video(bvid: str):
    """采集单个视频数据"""
    stat = await fetch_video_stat(bvid)
    if stat:
        DataStore.save_stat(stat)


async def collect_one(bvid: str) -> bool:
    """采集单个视频数据（供API调用，含首次视频信息获取）"""
    if not DataStore.get_info(bvid):
        info = await fetch_video_info(bvid)
        if not info:
            return False
        DataStore.save_info(info)

    stat = await fetch_video_stat(bvid)
    if not stat:
        return False
    DataStore.save_stat(stat)
    return True


def add_video_job(bvid: str):
    """为视频添加定时采集任务"""
    interval = DataStore.get_effective_interval(bvid)
    jid = _job_id(bvid)
    if scheduler.get_job(jid):
        scheduler.remove_job(jid)
    scheduler.add_job(
        _collect_video, "interval", seconds=interval,
        id=jid, args=[bvid], replace_existing=True,
    )


def remove_video_job(bvid: str):
    """移除视频的定时采集任务"""
    jid = _job_id(bvid)
    if scheduler.get_job(jid):
        scheduler.remove_job(jid)


def reschedule_video(bvid: str, seconds: int):
    """修改单个视频的采集间隔"""
    jid = _job_id(bvid)
    if scheduler.get_job(jid):
        scheduler.reschedule_job(jid, trigger="interval", seconds=seconds)
    else:
        add_video_job(bvid)


def reschedule_default_videos(seconds: int):
    """全局默认间隔变更时，更新所有跟随全局的视频"""
    for bvid in DataStore.get_monitored_bvids():
        if DataStore.get_video_interval(bvid) is None:
            reschedule_video(bvid, seconds)


def start_scheduler():
    """启动调度器，为每个已监控视频创建独立采集任务"""
    for bvid in DataStore.get_monitored_bvids():
        add_video_job(bvid)
    scheduler.start()


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
