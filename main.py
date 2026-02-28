"""B站视频数据实时监控工具 - 主入口"""

import argparse
import setproctitle
setproctitle.setproctitle("bv-monitor")

import uvicorn
from app import create_app

app = create_app()


def start():
    """启动服务"""
    parser = argparse.ArgumentParser(description="B站视频数据实时监控工具")
    parser.add_argument("-p", "--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    args = parser.parse_args()
    uvicorn.run("main:app", host="127.0.0.1", port=args.port, reload=True)


if __name__ == "__main__":
    start()
