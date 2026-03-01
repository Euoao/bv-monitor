"""B站API接口封装

优化：使用共享 httpx.AsyncClient 复用连接池与 SSL 上下文，
避免每次 API 调用都创建新客户端实例。
"""

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


# ── 共享 HTTP 客户端（复用连接池，降低内存与连接开销）──

_client: httpx.AsyncClient | None = None


def init_client():
    """初始化共享客户端（应用启动时调用）"""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(headers=HEADERS, timeout=10)


async def close_client():
    """关闭共享客户端（应用关闭时调用）"""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _get_client() -> httpx.AsyncClient:
    """获取共享客户端（若未初始化则自动创建）"""
    global _client
    if _client is None or _client.is_closed:
        init_client()
    return _client


async def fetch_video_info(bvid: str) -> VideoInfo | None:
    """获取视频基本信息"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    try:
        resp = await _get_client().get(url, params=params)
        data = resp.json()
        if data["code"] != 0:
            return None
        d = data["data"]
        return VideoInfo(
            bvid=bvid,
            title=d["title"],
            pic=d["pic"].replace("http://", "https://"),
            owner_name=d["owner"]["name"],
            desc=d["desc"],
        )
    except Exception:
        return None


async def fetch_video_stat(bvid: str) -> VideoStat | None:
    """获取视频统计数据"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    try:
        resp = await _get_client().get(url, params=params)
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
