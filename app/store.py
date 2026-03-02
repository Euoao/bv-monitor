"""数据存储模块 - SQLite + JSON 持久化

文件结构：
  data/stats.db           统计数据（SQLite，所有视频共用）
  data/{bvid}.json        视频元信息 + 采集间隔（小文件，低频读写）
  data/_config.json        全局配置
  data/_monitors.json      监控列表

迁移说明：
  启动时自动检测旧格式数据并迁移到 SQLite：
  - 旧 JSON 文件中的 stats 数组 → SQLite
  - JSONL 文件 → SQLite（完成后重命名为 .jsonl.bak）
"""

import json
import sqlite3
from datetime import datetime, timedelta
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

# ── SQLite 数据库 ──

_DB_PATH = DATA_DIR / "stats.db"
_conn: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    """获取数据库连接（懒初始化，WAL 模式）"""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")        # 读写并发
        _conn.execute("PRAGMA synchronous=NORMAL")       # 平衡性能与安全
        _conn.execute("PRAGMA cache_size=-2000")         # 2MB 缓存
        _conn.row_factory = sqlite3.Row
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection):
    """创建表结构和索引"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS video_stats (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            bvid      TEXT    NOT NULL,
            view      INTEGER NOT NULL,
            "like"    INTEGER NOT NULL,
            coin      INTEGER NOT NULL,
            favorite  INTEGER NOT NULL,
            share     INTEGER NOT NULL,
            danmaku   INTEGER NOT NULL,
            reply     INTEGER NOT NULL,
            timestamp TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_bvid_ts
        ON video_stats (bvid, timestamp)
    """)
    conn.commit()


def close_db():
    """关闭数据库连接（应用退出时调用）"""
    global _conn
    if _conn:
        _conn.close()
        _conn = None


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

    # ── 旧格式迁移 ──

    _migrated: set[str] = set()

    @classmethod
    def _ensure_migrated(cls, bvid: str):
        """确保旧格式数据已迁移到 SQLite（每个 bvid 只检查一次）"""
        if bvid not in cls._migrated:
            cls._migrate_old_json(bvid)
            cls._migrate_jsonl(bvid)
            cls._migrated.add(bvid)

    @classmethod
    def _migrate_old_json(cls, bvid: str):
        """若旧 JSON 文件中包含 stats 数组，迁移到 SQLite 并清除"""
        meta_path = cls._meta_file(bvid)
        if not meta_path.exists():
            return
        with cls._lock:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            stats = data.pop("stats", None)
            if stats is None:
                return
            # 将 stats 导入 SQLite
            db = _get_db()
            batch = []
            for r in stats:
                batch.append((
                    r.get("bvid", bvid), r["view"], r["like"], r["coin"],
                    r["favorite"], r["share"], r["danmaku"], r["reply"],
                    r["timestamp"],
                ))
            if batch:
                db.executemany(
                    'INSERT INTO video_stats (bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', batch
                )
                db.commit()
            # 回写元信息文件（已移除 stats）
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def _migrate_jsonl(cls, bvid: str):
        """将 JSONL 文件数据导入 SQLite，完成后重命名原文件为 .jsonl.bak"""
        jsonl_path = DATA_DIR / f"{bvid}_stats.jsonl"
        if not jsonl_path.exists():
            return
        with cls._lock:
            db = _get_db()
            batch = []
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                        batch.append((
                            r.get("bvid", bvid), r["view"], r["like"], r["coin"],
                            r["favorite"], r["share"], r["danmaku"], r["reply"],
                            r["timestamp"],
                        ))
                    except (json.JSONDecodeError, KeyError):
                        continue
            if batch:
                db.executemany(
                    'INSERT INTO video_stats (bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', batch
                )
                db.commit()
            # 迁移完成，备份原文件
            jsonl_path.rename(jsonl_path.with_suffix(".jsonl.bak"))

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

    # ── 统计数据（SQLite）──

    @classmethod
    def save_stat(cls, stat: VideoStat):
        """保存一条统计数据"""
        bvid = stat.bvid
        cls._ensure_migrated(bvid)
        db = _get_db()
        with cls._lock:
            db.execute(
                'INSERT INTO video_stats (bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (bvid, stat.view, stat.like, stat.coin, stat.favorite,
                 stat.share, stat.danmaku, stat.reply, stat.timestamp),
            )
            db.commit()

    @classmethod
    def get_stats(cls, bvid: str, limit: int | None = None) -> list[dict]:
        """获取统计数据

        Args:
            bvid: 视频 BV 号
            limit: 最多返回最近 N 条记录。None 表示全部。
        """
        cls._ensure_migrated(bvid)
        db = _get_db()
        if limit is not None and limit > 0:
            rows = db.execute(
                'SELECT bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp '
                'FROM video_stats WHERE bvid = ? ORDER BY timestamp DESC LIMIT ?',
                (bvid, limit),
            ).fetchall()
            # 反转为时间正序
            return [dict(r) for r in reversed(rows)]
        else:
            rows = db.execute(
                'SELECT bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp '
                'FROM video_stats WHERE bvid = ? ORDER BY timestamp',
                (bvid,),
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_latest_stat(cls, bvid: str) -> dict | None:
        """获取最新一条统计数据"""
        cls._ensure_migrated(bvid)
        db = _get_db()
        row = db.execute(
            'SELECT bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp '
            'FROM video_stats WHERE bvid = ? ORDER BY timestamp DESC LIMIT 1',
            (bvid,),
        ).fetchone()
        return dict(row) if row else None

    # ── 时间范围查询 + 降采样 ──

    # 降采样：前端图表有效分辨率有限，超过此数量则等间隔取点
    MAX_POINTS = 1000

    # range 字符串 → timedelta 映射
    _RANGE_MAP: dict[str, timedelta] = {
        "1h":  timedelta(hours=1),
        "6h":  timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d":  timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }

    @classmethod
    def get_stats_ranged(
        cls,
        bvid: str,
        range_str: str | None = None,
        start: str | None = None,
        end: str | None = None,
        max_points: int | None = None,
    ) -> list[dict]:
        """按时间范围查询统计数据，自动降采样

        Args:
            bvid: 视频 BV 号
            range_str: 快捷时间范围 "1h"/"6h"/"24h"/"7d"/"30d"/"90d"/"all"
            start: 起始时间 "YYYY-MM-DD HH:mm:ss"（与 end 配合使用）
            end:   结束时间 "YYYY-MM-DD HH:mm:ss"
            max_points: 最大返回数据点数，默认 MAX_POINTS
        """
        cls._ensure_migrated(bvid)
        db = _get_db()

        if max_points is None:
            max_points = cls.MAX_POINTS

        # 确定时间范围
        ts_start, ts_end = cls._resolve_time_range(range_str, start, end)

        # 构建查询
        cols = 'bvid, view, "like", coin, favorite, share, danmaku, reply, timestamp'
        if ts_start and ts_end:
            where = "WHERE bvid = ? AND timestamp >= ? AND timestamp <= ?"
            params: tuple = (bvid, ts_start, ts_end)
        elif ts_start:
            where = "WHERE bvid = ? AND timestamp >= ?"
            params = (bvid, ts_start)
        else:
            where = "WHERE bvid = ?"
            params = (bvid,)

        # 统计总数，决定是否降采样
        total = db.execute(
            f"SELECT COUNT(*) FROM video_stats {where}", params
        ).fetchone()[0]

        if total <= max_points:
            # 不需要降采样，直接返回
            rows = db.execute(
                f"SELECT {cols} FROM video_stats {where} ORDER BY timestamp",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

        # 需要降采样：等间隔取点
        step = total // max_points
        rows = db.execute(
            f"""
            SELECT {cols} FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp) AS _rn
                FROM video_stats {where}
            )
            WHERE _rn = 1 OR _rn % ? = 0 OR _rn = ?
            ORDER BY timestamp
            """,
            (*params, step, total),
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def _resolve_time_range(
        cls,
        range_str: str | None,
        start: str | None,
        end: str | None,
    ) -> tuple[str | None, str | None]:
        """解析时间范围参数，返回 (start_ts, end_ts)"""
        if range_str:
            if range_str == "all":
                return None, None
            delta = cls._RANGE_MAP.get(range_str)
            if delta:
                now = datetime.now()
                ts_start = (now - delta).strftime("%Y-%m-%d %H:%M:%S")
                return ts_start, None
            return None, None
        if start:
            return start, end
        return None, None

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

    # ── 数据归档清理 ──

    @classmethod
    def cleanup_old_data(cls):
        """定期清理：保留近期原始数据，远期数据降采样

        策略（默认）：
        - 最近 7 天   → 保留全部原始数据
        - 7 ~ 30 天   → 降采样为每 5 分钟一条
        - 30 ~ 90 天  → 降采样为每 30 分钟一条
        - > 90 天     → 降采样为每小时一条
        """
        config = cls.get_config()
        if config.get("retention_enabled") is False:
            return  # 用户可在配置中禁用

        db = _get_db()
        now = datetime.now()

        cutoff_7d  = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cutoff_90d = (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")

        with cls._lock:
            # 7~30 天：每 5 分钟保留一条
            cls._downsample(db, cutoff_30d, cutoff_7d, 5)

            # 30~90 天：每 30 分钟保留一条
            cls._downsample(db, cutoff_90d, cutoff_30d, 30)

            # > 90 天：每小时保留一条
            cls._downsample(db, None, cutoff_90d, 60)

            db.commit()
            db.execute("PRAGMA optimize")

    @classmethod
    def _downsample(cls, db: sqlite3.Connection, ts_start: str | None, ts_end: str, minutes: int):
        """删除某时间段中多余的数据，每 `minutes` 分钟只保留第一条

        通过按 (bvid, 时间窗口) 分组，保留每组中 id 最小的记录，删除其余记录。
        """
        if ts_start:
            where = "timestamp >= ? AND timestamp < ?"
            params = (ts_start, ts_end)
        else:
            where = "timestamp < ?"
            params = (ts_end,)

        # 构建时间窗口表达式：将分钟数截断到 `minutes` 的整数倍
        # strftime('%M') 返回 "00"~"59"，CAST 为整数后整除再乘回
        window_expr = (
            "bvid || strftime('%Y-%m-%d %H:', timestamp) || "
            f"CAST(CAST(strftime('%M', timestamp) AS INTEGER) / {minutes} * {minutes} AS TEXT)"
        )

        db.execute(f"""
            DELETE FROM video_stats
            WHERE {where}
              AND id NOT IN (
                  SELECT MIN(id)
                  FROM video_stats
                  WHERE {where}
                  GROUP BY {window_expr}
              )
        """, params + params)

    # ── 私有方法 ──

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
