"""本地端到端验证脚本（网络受限环境用）：

真实链路：TTS 中文语音 -> ffmpeg -> 硅基流动 SenseVoice ASR -> DeepSeek-V3 整理
        -> Markdown 笔记 -> git commit。

抖音元数据解析跳因测试机海外出口被风控，用 meta_override 注入；
国内网络运行 `douyin-catcher process "<分享文本>"` 即为完整链路。
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from douyin_catcher.audio import FFMPEG
from douyin_catcher.asr import transcribe
from douyin_catcher.config import config
from douyin_catcher.note import save_note
from douyin_catcher.pipeline import _git_commit
from douyin_catcher.summarizer import summarize

TEXT = (
    "大家好，今天用一分钟讲清楚什么是复利。复利就是利息也能产生利息。"
    "假设你有一万块钱，年利率百分之十，第一年你赚一千块。"
    "第二年你不是只赚一千，而是赚一千一百块，因为上一年的利息也开始生息了。"
    "三十年后，这一万块钱会变成十七万四千块，是本金的十七倍。"
    "所以复利的核心是时间，开始得越早，曲线越陡。记住这句话：时间是最好的朋友。"
)


async def main() -> int:
    work = Path("data/e2e")
    work.mkdir(parents=True, exist_ok=True)
    aiff = work / "tts.aiff"
    mp3 = work / "tts.mp3"

    print("[1/5] 合成中文语音...")
    subprocess.run(
        ["say", "-v", "Eddy (中文（中国大陆）)", TEXT, "-o", str(aiff)],
        check=True,
    )
    subprocess.run(
        [FFMPEG, "-y", "-i", str(aiff), "-acodec", "libmp3lame", "-ar", "16000",
         "-ac", "1", "-b:a", "64k", str(mp3)],
        check=True, capture_output=True,
    )
    print(f"      音频就绪: {mp3} ({mp3.stat().st_size} bytes)")

    print("[2/5] 真实 ASR（硅基流动 SenseVoice）...")
    transcript = await transcribe(mp3)
    print(f"      转写 {len(transcript)} 字: {transcript[:60]}...")
    if len(transcript) < 20:
        print("      [警告] 转写过短")

    print("[3/5] 真实 LLM 整理（DeepSeek-V3）...")
    summary = await summarize(
        title="一分钟讲清复利", author="Eddy", transcript=transcript
    )
    print(f"      笔记 {len(summary)} 字, 含小节: {[l for l in summary.splitlines() if l.startswith('##')][:4]}")

    print("[4/5] 生成 Markdown 笔记...")
    meta = {
        "aweme_id": "7703565610995185235",  # E2E 真实测试视频 ID
        "title": "一分钟讲清复利（E2E 验证）",
        "author": "douyin-catcher E2E",
    }
    note = save_note(meta, summary=summary, transcript=transcript, notes_dir=config.NOTES_DIR)
    print(f"      笔记: {note}")

    print("[5/5] git 提交...")
    result = _git_commit(note, Path.cwd())
    print(f"      git: {result}")

    aiff.unlink(missing_ok=True)
    mp3.unlink(missing_ok=True)
    print(f"\nE2E 完成: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
