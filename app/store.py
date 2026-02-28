"""数据存储模块 - JSON + JSONL 持久化

文件结构：
  data/{bvid}.json        视频元信息 + 采集间隔（小文件，低频读写）
  data/{bvid}_stats.jsonl  统计数据，每行一条 JSON（追加写入，高频）
  data/_config.json        全局配置
  data/_monitors.json      监控列表
"""

import json
from pathlib import Path
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

    # ── 文件路径 ──

    @classmethod
    def _meta_file(cls, bvid: str) -> Path:
        """视频元信息文件（info + interval）"""
        return DATA_DIR / f"{bvid}.json"

    @classmethod
    def _stats_file(cls, bvid: str) -> Path:
        """视频统计数据文件（JSONL 格式）"""
        return DATA_DIR / f"{bvid}_stats.jsonl"

    # ── 旧格式迁移 ──

    @classmethod
    def _migrate_if_needed(cls, bvid: str):
        """若旧 JSON 文件中包含 stats 数组，迁移到 JSONL 并清除"""
        meta_path = cls._meta_file(bvid)
        if not meta_path.exists():
            return
        with cls._lock:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            stats = data.pop("stats", None)
            if stats is None:
                return
            # 将 stats 逐行写入 JSONL
            stats_path = cls._stats_file(bvid)
            with open(stats_path, "a", encoding="utf-8") as f:
                for record in stats:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            # 回写元信息文件（已移除 stats）
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 视频信息 ──

    @classmethod
    def save_info(cls, info: VideoInfo):
        """保存视频基本信息"""
        filepath = cls._meta_file(info.bvid)
        with cls._lock:
            data = cls._load_meta(filepath)
            data["info"] = asdict(info)
            cls._save_meta(filepath, data)

    @classmethod
    def get_info(cls, bvid: str) -> dict | None:
        """获取视频基本信息"""
        filepath = cls._meta_file(bvid)
        data = cls._load_meta(filepath)
        return data.get("info")

    # ── 统计数据（JSONL 追加写入）──

    @classmethod
    def save_stat(cls, stat: VideoStat):
        """追加一条统计数据（仅追加一行，不读取整个文件）"""
        bvid = stat.bvid
        cls._ensure_migrated(bvid)
        stats_path = cls._stats_file(bvid)
        line = json.dumps(asdict(stat), ensure_ascii=False) + "\n"
        with cls._lock:
            with open(stats_path, "a", encoding="utf-8") as f:
                f.write(line)

    @classmethod
    def get_stats(cls, bvid: str) -> list[dict]:
        """获取所有统计数据"""
        cls._ensure_migrated(bvid)
        stats_path = cls._stats_file(bvid)
        if not stats_path.exists():
            return []
        results = []
        with open(stats_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        return results

    @classmethod
    def get_latest_stat(cls, bvid: str) -> dict | None:
        """高效获取最新一条统计数据（从文件末尾读取）"""
        cls._ensure_migrated(bvid)
        stats_path = cls._stats_file(bvid)
        if not stats_path.exists():
            return None
        # 从末尾往回读，找到最后一个非空行
        try:
            with open(stats_path, "rb") as f:
                f.seek(0, 2)  # 移到文件末尾
                size = f.tell()
                if size == 0:
                    return None
                # 从末尾向前读取，最多 4KB 足够一行
                chunk_size = min(4096, size)
                f.seek(size - chunk_size)
                chunk = f.read().decode("utf-8")
                lines = chunk.strip().rsplit("\n", 1)
                last_line = lines[-1].strip()
                if last_line:
                    return json.loads(last_line)
        except (json.JSONDecodeError, OSError):
            pass
        return None

    # ── 监控列表 ──

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

    # ── 单视频采集间隔 ──

    @classmethod
    def get_video_interval(cls, bvid: str) -> int | None:
        """获取视频专属采集间隔，None 表示跟随全局默认"""
        filepath = cls._meta_file(bvid)
        data = cls._load_meta(filepath)
        return data.get("interval")

    @classmethod
    def set_video_interval(cls, bvid: str, interval: int | None):
        """设置视频专属采集间隔，None 表示跟随全局默认"""
        filepath = cls._meta_file(bvid)
        with cls._lock:
            data = cls._load_meta(filepath)
            if interval is None:
                data.pop("interval", None)
            else:
                data["interval"] = interval
            cls._save_meta(filepath, data)

    @classmethod
    def get_effective_interval(cls, bvid: str) -> int:
        """获取视频的实际采集间隔（专属间隔优先，否则用全局默认）"""
        vi = cls.get_video_interval(bvid)
        if vi is not None:
            return vi
        return cls.get_config().get("interval", 30)

    # ── 私有方法 ──

    # 记录已迁移的 bvid，避免每次 save_stat 都检查文件
    _migrated: set[str] = set()

    @classmethod
    def _ensure_migrated(cls, bvid: str):
        """确保旧格式数据已迁移（每个 bvid 只检查一次）"""
        if bvid not in cls._migrated:
            cls._migrate_if_needed(bvid)
            cls._migrated.add(bvid)

    @classmethod
    def _load_meta(cls, filepath: Path) -> dict:
        if not filepath.exists():
            return {}
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _save_meta(cls, filepath: Path, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
