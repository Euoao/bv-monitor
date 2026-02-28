"""数据存储模块 - 使用JSON文件持久化"""

import json
from pathlib import Path
from datetime import datetime
from threading import Lock
from dataclasses import asdict

from .bilibili import VideoStat, VideoInfo

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 默认配置
_DEFAULT_CONFIG = {
    "interval": 30,  # 采集间隔（秒）
}


class DataStore:
    """线程安全的数据存储"""

    _lock = Lock()

    # ── 配置 ──

    @classmethod
    def _config_file(cls) -> Path:
        return DATA_DIR / "_config.json"

    @classmethod
    def get_config(cls) -> dict:
        """获取全局配置"""
        f = cls._config_file()
        if not f.exists():
            return dict(_DEFAULT_CONFIG)
        with open(f, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        # 补齐默认值
        for k, v in _DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg

    @classmethod
    def set_config(cls, patch: dict):
        """更新配置（合并写入）"""
        with cls._lock:
            cfg = cls.get_config()
            cfg.update(patch)
            with open(cls._config_file(), "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, ensure_ascii=False, indent=2)

    @classmethod
    def _get_file(cls, bvid: str) -> Path:
        """获取存储文件路径"""
        return DATA_DIR / f"{bvid}.json"

    @classmethod
    def save_info(cls, info: VideoInfo):
        """保存视频基本信息"""
        filepath = cls._get_file(info.bvid)
        with cls._lock:
            data = cls._load_raw(filepath)
            data["info"] = asdict(info)
            cls._save_raw(filepath, data)

    @classmethod
    def save_stat(cls, stat: VideoStat):
        """追加一条统计数据"""
        filepath = cls._get_file(stat.bvid)
        with cls._lock:
            data = cls._load_raw(filepath)
            if "stats" not in data:
                data["stats"] = []
            data["stats"].append(asdict(stat))
            cls._save_raw(filepath, data)

    @classmethod
    def get_info(cls, bvid: str) -> dict | None:
        """获取视频基本信息"""
        filepath = cls._get_file(bvid)
        data = cls._load_raw(filepath)
        return data.get("info")

    @classmethod
    def get_stats(cls, bvid: str) -> list[dict]:
        """获取所有统计数据"""
        filepath = cls._get_file(bvid)
        data = cls._load_raw(filepath)
        return data.get("stats", [])

    @classmethod
    def get_monitored_bvids(cls) -> list[str]:
        """获取所有正在监控的BV号"""
        monitor_file = DATA_DIR / "_monitors.json"
        if not monitor_file.exists():
            return []
        with open(monitor_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def add_monitor(cls, bvid: str):
        """添加监控"""
        with cls._lock:
            monitors = cls.get_monitored_bvids()
            if bvid not in monitors:
                monitors.append(bvid)
                with open(DATA_DIR / "_monitors.json", "w", encoding="utf-8") as f:
                    json.dump(monitors, f)

    @classmethod
    def remove_monitor(cls, bvid: str):
        """移除监控"""
        with cls._lock:
            monitors = cls.get_monitored_bvids()
            if bvid in monitors:
                monitors.remove(bvid)
                with open(DATA_DIR / "_monitors.json", "w", encoding="utf-8") as f:
                    json.dump(monitors, f)

    @classmethod
    def _load_raw(cls, filepath: Path) -> dict:
        if not filepath.exists():
            return {}
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _save_raw(cls, filepath: Path, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
