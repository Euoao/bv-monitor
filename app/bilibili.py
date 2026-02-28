"""B站API接口封装"""

import httpx
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VideoInfo:
    """视频基本信息"""
    bvid: str
    title: str
    pic: str  # 封面图URL
    owner_name: str
    desc: str


@dataclass
class VideoStat:
    """视频统计数据"""
    bvid: str
    view: int       # 播放量
    like: int       # 点赞
    coin: int       # 投币
    favorite: int   # 收藏
    share: int      # 分享
    danmaku: int    # 弹幕
    reply: int      # 评论
    timestamp: str  # 采集时间


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


async def fetch_video_info(bvid: str) -> VideoInfo | None:
    """获取视频基本信息"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data["code"] != 0:
                return None
            d = data["data"]
            return VideoInfo(
                bvid=bvid,
                title=d["title"],
                pic=d["pic"],
                owner_name=d["owner"]["name"],
                desc=d["desc"],
            )
        except Exception:
            return None


async def fetch_video_stat(bvid: str) -> VideoStat | None:
    """获取视频统计数据"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data["code"] != 0:
                return None
            stat = data["data"]["stat"]
            return VideoStat(
                bvid=bvid,
                view=stat["view"],
                like=stat["like"],
                coin=stat["coin"],
                favorite=stat["favorite"],
                share=stat["share"],
                danmaku=stat["danmaku"],
                reply=stat["reply"],
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception:
            return None
