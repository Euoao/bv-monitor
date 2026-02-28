"""定时采集模块 - 定期拉取B站视频数据"""

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from .bilibili import fetch_video_stat, fetch_video_info
from .store import DataStore

scheduler = BackgroundScheduler()


def _collect_job():
    """采集任务（在后台线程中运行，内部创建事件循环执行异步函数）"""
    bvids = DataStore.get_monitored_bvids()
    if not bvids:
        return

    loop = asyncio.new_event_loop()
    try:
        for bvid in bvids:
            stat = loop.run_until_complete(fetch_video_stat(bvid))
            if stat:
                DataStore.save_stat(stat)
    finally:
        loop.close()


def start_scheduler():
    """启动定时采集，每60秒采集一次"""
    scheduler.add_job(_collect_job, "interval", seconds=60, id="collect_stats", replace_existing=True)
    scheduler.start()


def shutdown_scheduler():
    """关闭调度器"""
    scheduler.shutdown(wait=False)
