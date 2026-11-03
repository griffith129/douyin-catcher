# douyin-catcher

手机抖音「分享 → 复制链接」→ 电脑自动下载 → 语音转文字 → LLM 整理 → Markdown 学习笔记 → git 入库。

## 架构

```
安卓手机 [分享→复制链接] → HTTP POST /link（FastAPI :8787）
  → 链接队列（文件持久化、去重）→ worker
  → 解析元数据（iesdouyin 分享页 _ROUTER_DATA，无水印地址）
  → 下载视频 → ffmpeg 提取音频
  → 硅基流动 SenseVoice 转文字
  → LLM（DeepSeek-V3）整理为结构化笔记
  → notes/YYYY-MM-DD-标题-aweme_id.md（YAML frontmatter）→ git commit
```

## 快速开始

```bash
uv sync
cp .env.example .env   # 填入 SILICONFLOW_API_KEY

# 单条处理
uv run douyin-catcher process "8.97 复制打开抖音... https://v.douyin.com/xxxx/"

# 启动接收服务（安卓快捷指令 POST 到 http://<电脑IP>:8787/link，body: {"text": "<分享口令>"}）
uv run douyin-catcher serve --port 8787

# 处理队列积压
uv run douyin-catcher drain
```

## 安卓快捷指令（HTTP Request）

分享面板 → 抖音视频 → 分享到「快捷指令」→ 步骤：
1. 获取剪贴板（或接收分享文本）
2. 「获取 URL 内容」不需要；直接「获取文本」输入框内容
3. 「网络请求」：POST `http://<电脑IP>:8787/link`，Header `Content-Type: application/json`，Body `{"text": "分享文本"}`

同一链接自动去重；失败会记录日志不影响队列。

## 测试

```bash
uv run pytest    # 28 个单测（外部 HTTP 全部 mock）
```

## 配置（.env）

| 变量 | 默认 | 说明 |
|------|------|------|
| SILICONFLOW_API_KEY | - | 硅基流动 Key（ASR+LLM 共用） |
| ASR_PROVIDER | siliconflow | `siliconflow`（云端 SenseVoice）或 `whisper`（本地 faster-whisper，离线可用） |
| WHISPER_MODEL | base | 本地 whisper 模型（tiny/base/small） |
| ASR_MODEL | FunAudioLLM/SenseVoiceSmall | 云端语音识别模型 |
| LLM_API_KEY | - | LLM Key（缺省回退 SILICONFLOW_API_KEY） |
| LLM_BASE_URL | https://api.siliconflow.cn/v1 | OpenAI 兼容端点（可换 deepseek.com 等） |
| LLM_MODEL | deepseek-ai/DeepSeek-V3 | 笔记整理模型 |
| NOTES_DIR | notes | 笔记输出目录 |
| QUEUE_FILE | data/queue.txt | 链接队列文件 |

## 端到端验证

```bash
uv run python scripts/e2e_local.py   # TTS 语音 -> ASR -> LLM -> 笔记 -> git，全真实链路
```

注意：抖音分享页解析依赖国内网络出口（分享页按 UA+地域做 SSR，需 Android UA，代码已内置）；
海外出口会被风控返回空数据。`scripts/e2e_local.py` 用 meta_override 跳过该跳验证其余链路。
