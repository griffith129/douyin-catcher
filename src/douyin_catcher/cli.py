"""命令行入口。

  douyin-catcher process "<分享文本>"   # 立即处理一条链接
  douyin-catcher serve [--host H --port P]  # 启动接收服务（含后台 worker）
  douyin-catcher drain                 # 处理队列中所有积压链接
"""

import argparse
import asyncio
import sys

from .pipeline import process_link
from .queue import LinkQueue
from ._serve import run_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="douyin-catcher")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_process = sub.add_parser("process", help="立即处理一条分享文本")
    p_process.add_argument("text", nargs="?", help="分享口令（含链接）；省略则读 stdin")

    p_serve = sub.add_parser("serve", help="启动接收服务")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8787)

    sub.add_parser("drain", help="处理队列中所有积压链接")

    args = parser.parse_args(argv)

    if args.cmd == "process":
        text = args.text or sys.stdin.read()
        try:
            note = asyncio.run(process_link(text))
        except Exception as e:
            print(f"[失败] {e}", file=sys.stderr)
            return 1
        print(f"[完成] {note}")
        return 0

    if args.cmd == "serve":
        run_server(host=args.host, port=args.port)
        return 0

    if args.cmd == "drain":
        q = LinkQueue(__import__("douyin_catcher.config", fromlist=["config"]).config.QUEUE_FILE)
        failed = 0
        while (url := q.pop()) is not None:
            try:
                note = asyncio.run(process_link(url))
                print(f"[完成] {note}")
            except Exception as e:
                failed += 1
                print(f"[失败] {url}: {e}", file=sys.stderr)
        return 1 if failed else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
