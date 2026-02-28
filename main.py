"""B站视频数据实时监控工具 - 主入口"""

import setproctitle
setproctitle.setproctitle("bv-monitor")

import uvicorn
from app import create_app

app = create_app()


def start():
    """启动服务"""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
