"""链接队列：持久化到文件，天然去重。"""

import re
import threading
from pathlib import Path

from .parser import extract_urls

_URL_LINE_RE = re.compile(r"^\s*(\S+)\s*$")


class LinkQueue:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()
        self._lock = threading.Lock()

    def _read(self) -> list[str]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return [_URL_LINE_RE.match(line).group(1) for line in lines if line.strip()]

    def _write(self, links: list[str]) -> None:
        self._path.write_text("\n".join(links) + ("\n" if links else ""), encoding="utf-8")

    def push(self, share_text: str) -> bool:
        """从分享口令提取链接并入队；重复返回 False。"""
        urls = extract_urls(share_text)
        if not urls:
            raise ValueError("分享文本中未找到链接")
        url = urls[0]
        with self._lock:
            links = self._read()
            if url in links:
                return False
            links.append(url)
            self._write(links)
        return True

    def pop(self) -> str | None:
        with self._lock:
            links = self._read()
            if not links:
                return None
            url = links.pop(0)
            self._write(links)
        return url
