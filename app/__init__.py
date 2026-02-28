"""B站视频数据实时监控应用"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager

from .scheduler import start_scheduler, shutdown_scheduler
from .routes import router

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时开启定时采集，关闭时停止"""
    start_scheduler()
    yield
    shutdown_scheduler()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="BV Monitor", description="B站视频数据实时监控", lifespan=lifespan)

    # 挂载静态文件
    static_dir = BASE_DIR / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 注册路由
    app.include_router(router)

    return app
