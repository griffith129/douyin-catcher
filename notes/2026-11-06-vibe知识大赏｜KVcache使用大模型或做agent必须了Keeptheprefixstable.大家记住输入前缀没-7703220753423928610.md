---
aweme_id: '7703220753423928610'
title: "vibe知识大赏｜KV cache: 使用大模型或做 agent 必须了 \nKeep the prefix stable. 大家记住输入前缀没事别乱动就行哈哈哈\
  \ \n下一期有两个方向，一个是接着讲 KV cache 怎么变小、怎么存(我不是专家哈哈哈)，一个是开始讲 agent。想听哪个，评论区说一声 \n#大模型\
  \ #vibecoding #vibe知识大赏   #deepseek #agent"
author: henryz
source_url: https://www.douyin.com/video/7703220753423928610
captured_at: 2026-11-06 17:39
tags:
- douyin
- 知识收藏
---

# vibe知识大赏｜KV cache: 使用大模型或做 agent 必须了 
Keep the prefix stable. 大家记住输入前缀没事别乱动就行哈哈哈 
下一期有两个方向，一个是接着讲 KV cache 怎么变小、怎么存(我不是专家哈哈哈)，一个是开始讲 agent。想听哪个，评论区说一声 
#大模型 #vibecoding #vibe知识大赏   #deepseek #agent

## 一句话结论
复用相同输入前缀对应的模型中间计算结果，可以显著降低大模型与 Agent 的调用成本；因此保持前缀稳定是工程关键。

## 核心要点
- **KV Cache**（模型上次推理保存的 K/V 中间数据；命中时直接读回，不用重新计算）是降低重复输入成本的核心机制。
- 模型每层通过注意力让每个 **Token**（模型处理文本的基本单位）使用前面 Token 的信息，并计算 **QKV**（Query、Key、Value 三组向量）；后续 Token 会反复使用历史 Token 的 K/V，所以值得存下来。
- 大模型调用通常每次发送完整 **Message 列表**（System/User/Assistant 消息序列），下一次只在末尾追加，因此前缀高度重复，相同前缀产生的 KV 相同，可命中缓存。
- 命中缓存省掉的是前缀部分重新 **prefill**（把整段输入先读一遍）的计算；未命中则要重算。
- KV Cache 很大且解码时每步都要读，主要占 **HBM**（高带宽显存）；调用结束可迁到 CPU 内存/SSD，平台会有过期时间或额外收费。
- **Agent**（能调用模型与工具完成任务的智能体）场景输入长，视频称未命中缓存的重算费用可达命中时的 50 倍，所以缓存命中率是评价 **Harness**（智能体运行框架）的重要标准，保持前缀稳定非常重要。

## 关键细节
- 视频称同样 100 万 Token 输入，缓存命中与未命中的价格差约 50 倍（口播举例为“一块钱”与“两分钱”）。
- 这种只用前面、不用后面的方式（原文口播“Cozle”，即因果注意力）使一个 Token 的 KV 只由它和前面内容决定，后面追加内容不会改变已有前缀的 KV。
- 一个对话聊满上下文长度时，KV Cache 接近 5GB；一张 H100 最多还能放三四个这样的对话。
- 解码时模型逐个输出 Token，每出一个都要读一遍 KV Cache，所以它必须放在 HBM。
- 优化方向：改模型结构让 KV Cache 变小并可在推理时量化；Pager Tension（疑为 PagedAttention）减少显存浪费；Radix Tension（疑为 RadixAttention）让留下的 KV Cache 更容易复用。
- OpenRouter 统计：Agent 流量里接近九成（原文“九层”）输入 Token 命中了缓存。
- Agent 的 Message 列表由 System/User/Assistant 消息组成；Context Engineering、Harness Engineering 很大一部分是在管理这个列表：放什么、按什么顺序、怎么压缩。
- 删除或修改前文会改变前缀，从改动处开始的后续缓存全部作废，需要重新计算。

## 原文没有讲清的问题
- “100 万 Token 命中/未命中相差 50 倍”的具体计价口径和对应模型是什么？
- KV Cache 的过期时间、跨请求迁移到 CPU 内存/SSD 的具体策略与成本如何权衡？
- Pager Tension、Radix Tension、GPU AMLA 等方案各自适用于什么场景、效果如何？
- 如何在“内容质量、前缀稳定、上下文压缩”之间做可操作的取舍？
- Harness 的缓存命中率如何测量、优化并纳入工程评价？

## 原文文案

同样100万个Token的输入,交给Dixix的API。每命中缓存要售一块钱,命中只售两分钱,差了五十倍。这个缓存就是KV Cash,是模型上一次算好,留下来的一份数据。命中的时候直接拿来用,不用再算。模型有几十层,每一层里都有一部叫Tension,让每个Token用上它前面所有Token的信息。做这一步是每个Token都会算出三组数字,叫QKV。新Token拿自己的Q和前面每个Token的KV,算出从每个Token那里取多少,V就是要取的内容。新Token的Q用完就不要了。前面Token的KV,后面每个新Token,在每一层都要再用。所以存下来的是KV和V,这就是KV Cash。这种只用前面不用后面的方式,叫Cozle,现在的大模型都是这样,所以一个Token的KV只有它和前面的内容我们决定,后面再加多少都不会变。前锥一样,算出来的KV就一模一样。现在掉用大模型,不管是Catbot还是Agent,每次发过去的都是一个Message列表,里面是SystemUser Assistant一条街一条的消息。下一次掉用就是在这个列表最后加一条,再整个发过去,所以前锥几乎每次都和上一次一样,只是最后多了一段。所以上一次掉用留下的KV,这一次还能用。命中了,前锥那一段的KV直接读回来,没命中,就要把这段重新Preview一遍,也就是第一期讲过的。模型先把整段输入读一遍的那一步。Preview很快,因为很多Token一起算,GPU的算利用的很满,但每个Token还是要把几十层从头到尾算一遍才能得到每一层的KV,命中省掉的就是这一整分计算。那为什么不把KVCache全部留着?因为它很大,那GPU SS120B来算,一个对话聊满它的上下文长度,KVCache就有将近5GB。抵扣的时候,也就是模型一个一个往外出Token的时候,每出一个都要把它读一遍,所以它只能放在HBM。一张H100放完60几GB的残处,最多也就再放三四个这样的对话。掉用结束以后,留下的KVCache不能一直站在HBM。它只在下词命中是读一次,可以挪到CPU内存SSD这种更便宜的地方。但存着重要站地方,这也是为什么Cache有过期时间,并且有的平台显入Cache要额外收费。所以这几年很多改进,都是为着KVCache做的。GPU AMLA改的是模型结构,让它变小,推理时还可以把它亮化。VLM的Pager Tension渐少线存浪费,SGline的Radix Tension让留下来的KVCache更容易被复用。Open Router的统计,现在Agent的流量里,接近九层的输入Token都命中了缓存。模型每次看到的,就只有这个Message是列表。所以现在做Agent,Context and Nearing,Harness and Nearing,很大一部分就是在管这个列表。放什么进去,按什么顺序,什么烧压缩。这里面有个冲突。内容决定模型做得好不好,潜追稳不稳,决定缓存那么能命中。比如像把前面没用的内容删掉,潜追就变了。从改动的地方开始,后面的缓存全部作费要重新算。做Agent都会特别在意缓存能不能命中,甚至可以说缓存命中率是评价Harness好坏的核心标准。Agent的Message会越来越长,没命中缓存时要重新算所有的KV,按Deepseek的价格,这部分的花费是命中时的50倍。所以一般来说,保持前追稳定非常重要,下一期有两个方向,一个是接着讲KVCache怎么变小怎么存,一个是我可能开始讲Agent了。想听哪个,再评论去说一声。
