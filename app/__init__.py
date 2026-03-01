"""B站视频数据实时监控应用"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager

from .bilibili import init_client, close_client
from .scheduler import start_scheduler, shutdown_scheduler
from .routes import router

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化资源，关闭时清理"""
    init_client()          # 初始化共享 HTTP 客户端
    start_scheduler()      # 启动定时采集
    yield
    shutdown_scheduler()   # 停止定时采集
    await close_client()   # 关闭共享 HTTP 客户端


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
