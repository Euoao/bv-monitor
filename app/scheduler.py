"""定时采集模块 - 定期抓取B站视频数据"""

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from .bilibili import fetch_video_stat, fetch_video_info
from .store import DataStore

scheduler = BackgroundScheduler()


def _collect_task():
    """定时采集任务（同步包装异步调用）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_collect_all())
    finally:
        loop.close()


async def _collect_all():
    """采集所有监控中的视频数据"""
    bvids = DataStore.get_monitored_bvids()
    for bvid in bvids:
        stat = await fetch_video_stat(bvid)
        if stat:
            DataStore.save_stat(stat)


async def collect_one(bvid: str) -> bool:
    """采集单个视频数据（供API调用）"""
    # 获取视频信息（如果还没有）
    if not DataStore.get_info(bvid):
        info = await fetch_video_info(bvid)
        if not info:
            return False
        DataStore.save_info(info)

    # 获取统计数据
    stat = await fetch_video_stat(bvid)
    if not stat:
        return False
    DataStore.save_stat(stat)
    return True


def start_scheduler():
    """启动定时采集，每30秒采集一次"""
    scheduler.add_job(_collect_task, "interval", seconds=30, id="collect_job")
    scheduler.start()


def shutdown_scheduler():
    """关闭调度器"""
    scheduler.shutdown(wait=False)
