"""B站视频数据实时监控应用"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    """创建 FastAPI 应用（基础骨架，后续逐步集成）"""
    app = FastAPI(title="BV Monitor", description="B站视频数据实时监控")

    # 挂载静态文件
    static_dir = BASE_DIR / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
