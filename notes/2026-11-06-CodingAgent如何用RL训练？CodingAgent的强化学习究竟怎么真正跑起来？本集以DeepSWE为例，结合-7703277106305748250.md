---
aweme_id: '7703277106305748250'
title: 'Coding Agent 如何用 RL 训练？ Coding Agent 的强化学习究竟怎么真正跑起来？

  本集以 DeepSWE 为例，结合 Qwen3-32B、R2E-Gym、rLLM 和 verl，深入源码拆解完整的 Agent RL Training Pipeline：

  SWEEnv 如何接入训练环境？

  Agent Rollout 如何生成 Trajectory？

  Token Mask 如何区分模型生成内容与环境反馈？

  Final Reward 如何写入训练轨迹？

  MC Return 如何计算？

  train_deepswe_32b.sh 如何启动分布式 PPO 训练？

  从 Agent 执行、轨迹构造、Reward 计算到 Policy Update，完整跑通 Coding Agent 的强化学习训练闭环。

  #CodingAgent  #AgentRL  #PPO  #Trajectory  #DeepSWE'
author: 猪头肉配Codex
source_url: https://www.douyin.com/video/7703277106305748250
captured_at: 2026-11-06 17:37
tags:
- douyin
- 知识收藏
---

# Coding Agent 如何用 RL 训练？ Coding Agent 的强化学习究竟怎么真正跑起来？
本集以 DeepSWE 为例，结合 Qwen3-32B、R2E-Gym、rLLM 和 verl，深入源码拆解完整的 Agent RL Training Pipeline：
SWEEnv 如何接入训练环境？
Agent Rollout 如何生成 Trajectory？
Token Mask 如何区分模型生成内容与环境反馈？
Final Reward 如何写入训练轨迹？
MC Return 如何计算？
train_deepswe_32b.sh 如何启动分布式 PPO 训练？
从 Agent 执行、轨迹构造、Reward 计算到 Policy Update，完整跑通 Coding Agent 的强化学习训练闭环。
#CodingAgent  #AgentRL  #PPO  #Trajectory  #DeepSWE

## 精华版

DeepSWE 是一条把 Coding Agent 真正纳入 RL 训练闭环的完整流水线，由三个部件组成：**R2E-Gym** 提供带 Docker 可执行环境的 SWE 任务（数据筛选后 4000+ 道题），**rLLM** 负责 Agent 与环境的交互编排、轨迹生成和训练脚本入口，**verl** 提供底层分布式 PPO 训练能力；基座模型是 **Qwen3-32B**，且不做专门的 Coding Agent SFT，直接从基座出发做 Agent RL。

执行链是：Qwen3 在 R2E-Gym 任务上经 **SWEEnv** 启动 Docker 环境 → Agent executor 多轮执行「构造 Prompt → Policy 产出 Action → 环境执行返回 observation → 更新 History」，直到任务结束或达到最大步长 → 得到 **trajectory** → 用 **Token Mask** 区分模型生成 token（mask=1，参与 loss）与环境反馈 token（mask=0，仅作上下文）→ 计算 **reward** → 经 verl 的 PPO 更新 Policy 参数。

评估分两个指标：**pass@1** 反映单次 rollout 的 Policy 能力，**pass@16** 含多次采样与 verifier 选择的共同贡献。资源上 GPU 推理与容器执行同时发生，官方要求至少 64 张 GPU、并行 512 个 Docker 容器（8 节点 × 8 卡）。

闭环的关键在于：环境反馈不进 loss 但进上下文，loss 只由模型自己生成的部分承担，模型才学得到「自己该怎么做动作」，而不是去拟合环境返回的文本。

---

## 一句话结论

DeepSWE 用 R2E-Gym 提供环境、rLLM 编排轨迹、verl 做分布式 PPO，把 Qwen3-32B 在 Docker 化的 SWE 任务上跑成一条「rollout → trajectory → token mask → reward → policy update」的完整 Agent RL 训练闭环。

## 核心要点

1. DeepSWE 由三部分组成：R2E-Gym 提供 SWE 任务与 Docker 环境，rLLM 负责 Agent 轨迹与训练流程编排，verl 提供底层分布式训练能力。
2. 训练起点是 Qwen3-32B 基座模型，没有先做专门的 Coding Agent SFT，而是直接从基座进入 Agent RL。
3. 训练数据来自 R2E-Gym 原始环境经筛选后形成的 4000 多个问题，每个问题都能进入 Docker 环境执行。
4. 一条 trajectory 中混有两类 token——模型生成的 token 和环境反馈的 token；前者 mask=1 参与 loss 计算，后者 mask=0 只作为条件上下文。
5. 训练脚本由 rLLM 提供、最终调用 verl 的 PPO 训练，关键参数（模型、训练/验证数据、学习率、worker 数量、异步执行、每个 problem 的采样数量）共同决定训练数据生成、advantage 计算与 Policy optimization。
6. 评估用两个指标：pass@1 衡量单次 Policy rollout 的成功率，pass@16 衡量 16 个候选经 verifier 选择后的效果。

## 关键细节

- **数据规模**：R2E-Gym 原始环境筛选后形成 4000 多个训练问题，每个问题对应一个可执行的 Docker 环境。
- **SWEEnv 的执行流程**：读入 R2E-Gym 数据 → 创建 SWE 环境 → 环境内部再创建代码环境 → 启动 Docker → Agent 在其中多轮操作 → 任务结束后算 reward → 关闭环境。代码量很少。
- **Agent executor 的单次循环**：环境初始化 → Agent 初始化 → 构造 Prompt → Policy 推理 → 解析 Action → 环境执行 Action 并返回 observation → 更新 Agent History → 直到任务结束或达到最大步长。
- **并行结构**：每个 Agent 对应一个独立的 environment，训练系统可以并行跑很多组「Agent + environment」。
- **资源分工**：GPU 侧负责 Qwen3 推理、rollout、reward 计算、Policy 训练与梯度更新；CPU 与容器侧负责 Docker image、代码库 checkout、编译、代码搜索、编译测试。
- **硬件要求**：官方文档要求至少 64 张 GPU、并行运行 512 个 Docker 容器；新配置为 8 个节点 × 每节点 8 张 GPU。
- **两指标的分工**：pass@1 体现训练后 Policy 自身的能力，pass@16 同时包含多次采样与 verifier 的贡献。

## 原文没有讲清的问题

1. **Final Reward 如何写入训练轨迹**：标题提出了这个问题，正文只说到「任务结束之后算 reward」，没有说明 reward 是只赋给最后一步、还是回填到整条 trajectory 的每个 token 上。
2. **MC Return 如何计算**：是否使用折扣因子、是否只做 Monte Carlo 回报而不引入 value 网络 baseline，正文未展开。
3. **reward 的具体构成**：是二值（测试全过/不过）还是部分得分（按测试通过比例给分），没有说明。
4. **数据筛选标准**：从 R2E-Gym 原始环境筛到 4000 多题，筛选依据（可复现性？难度？测试覆盖？）未讲。
5. **跳过 SFT 直接 RL 的依据**：为什么公开方案选择不做 Coding Agent SFT 直接 Agent RL，是否有对比实验支撑，正文只陈述了做法。
6. **verifier 的形态**：pass@16 中的 verifier 具体是什么、如何从 16 个候选里选择，未说明。
7. **异步执行机制**：参数里提到「异步执行」，但 rollout 与训练如何解耦、是否容忍 stale 数据，未展开。
8. **训练规模与耗时**：总训练步数、超参具体取值、64 GPU 配置下的实际吞吐与训练时长均未给出。

---

## 整体逻辑链条梳理

1. **确定训练对象与基座**：选定 Qwen3-32B 作为被训练的 Policy，且不经过 Coding Agent SFT 直接进入 RL。→ 成立前提：SWE 任务的 reward 足够稠密，能让基座模型从零开始学到有效行为。
2. **准备任务与环境**：R2E-Gym 经数据筛选产出 4000+ 个 SWE 问题，每个问题都能拉起一个 Docker 环境。→ 衔接上一环：有了可执行的、可判定对错的环境，reward 才有来源。
3. **把环境接进 Agent 框架**：SWEEnv 封装 R2E-Gym 环境，使 Agent 能在 Docker 内多轮执行代码操作。→ 衔接上一环：环境从「数据集」变成「可交互对象」，Agent 才能产生动作序列。
4. **Rollout 生成 trajectory**：rLLM 的 Agent executor 循环执行「构造 Prompt → Policy 出 Action → 环境执行 → 返回 observation → 更新 History」，直到任务结束或达到最大步长。→ 衔接上一环：交互被记录成一条带角色的序列，即训练样本。
5. **Token Mask 区分来源**：trajectory 中模型生成的 token 置 mask=1，环境反馈的 token 置 mask=0，只有前者参与 loss。→ 衔接上一环：这一步决定了「学什么」，避免模型去拟合测试输出、工具返回等它不该生成的内容。
6. **计算 reward 并回填**：任务结束后算 reward，作为这条 trajectory 的优化信号。→ 衔接上一环：有了 reward，才有从序列到梯度的桥梁。
7. **PPO 更新 Policy**：rLLM 训练脚本调用 verl，按采样数量等参数算 advantage、做 Policy optimization，更新 Qwen3-32B 参数。→ 衔接上一环：参数更新后，下一轮 rollout 的 Policy 变强，闭环回到第 4 环。
8. **评估与资源支撑**：用 pass@1 与 pass@16 衡量效果；整个过程中 GPU 推理与 CPU/容器执行并行发生，需要 64 GPU + 512 容器的规模。→ 这是闭环能持续运转的物理条件，也是整条链的成本边界。

---

## 详细拆解

### 对应链条第 1 环：DeepSWE 的组成与基座

**DeepSWE**
- 一句话本质：一个把 SWE 任务环境、Agent 轨迹编排和分布式 RL 训练拼装成完整训练闭环的方案。
- 结构化拆解：
  - 由三部分构成：R2E-Gym（环境与任务来源）、rLLM（轨迹与流程编排）、verl（分布式训练）。
  - 工作方式：以 Qwen3-32B 为基座，在 R2E-Gym 的 Docker 任务上做 rollout 生成轨迹，算 reward 后用 verl 做 PPO 更新。
- 作用定位：它是本文档的主题容器——前面拆过的任务环境、trajectory、reward 三个组件，最终都由它装进真正的训练系统里。

**R2E-Gym**
- 一句话本质：提供 SWE 任务及其可执行 Docker 环境的数据来源。
- 结构化拆解：
  - 解决什么问题：给 Agent 一批「有明确对错、能真实跑起来」的编程任务。
  - 关键机制：原始环境经过数据筛选，形成 4000 多个训练问题；每个问题都能拉起一个 Docker 环境执行。
- 作用定位：训练数据与环境供给方，没有它就没有 rollout 的场地。

**rLLM**
- 一句话本质：负责 Agent 与环境的交互编排、轨迹生成，并提供训练脚本入口的框架。
- 结构化拆解：
  - 由 Agent executor 组织多轮执行；
  - 负责构造 Prompt、解析 Action、维护 Agent History；
  - 提供训练脚本，最终调用 verl 的 PPO 训练。
- 作用定位：位于环境与训练器之间的中间层，把「交互」翻译成「训练样本」。

**verl**
- 一句话本质：提供底层分布式 RL 训练能力的框架。
- 结构化拆解：
  - 承担 PPO 训练流程；
  - 由 rLLM 的训练脚本调用；
  - 相关参数（模型、训练/验证数据、学习率、worker 数量、异步执行、每个 problem 的采样数量）影响训练数据生成、advantage 计算与 Policy optimization。
- 作用定位：真正执行参数更新的那一层，是闭环的落点。

**Qwen3-32B**
- 一句话本质：被训练的基座大模型，参数量 32B。
- 结构化拆解：
  - 作为 Policy 参与 rollout，产出 Action；
  - 其参数在 PPO 阶段被更新；
  - 训练中不做 Coding Agent SFT，直接从基座进入 Agent RL。
- 作用定位：整条链的学习主体，所有 mask、reward、advantage 最终都作用在它身上。

### 对应链条第 2 环：SWEEnv 把环境接进 Agent 框架

**SWEEnv**
- 一句话本质：把 R2E-Gym 的 SWE 环境封装并接入 Agent 框架的适配层。
- 结构化拆解：
  - 执行顺序：读入 R2E-Gym 数据 → 创建 SWE 环境 → 环境内部创建代码环境 → 启动 Docker → Agent 在其中执行多轮操作 → 任务结束算 reward → 关闭环境。
  - 每个任务对应一个独立环境，可并行多组。
  - 实现代码量很少，核心工作是把「数据集条目」变成「可交互的环境实例」。
- 作用定位：它是数据与 Agent 之间的接口；理解它，才能明白 rollout 里的 observation 从哪来。

### 对应链条第 3 环：Rollout 生成 Trajectory

**Trajectory（轨迹）**
- 一句话本质：一次完整任务执行中按时间顺序记录下来的全部交互序列。
- 结构化拆解：
  - 由两部分内容交替构成：模型生成的 token（Prompt、推理、Action）和环境反馈的 token（测试结果、工具结果等）。
  - 生成过程：环境初始化 → Agent 初始化 → 构造 Prompt → Policy 推理 → 解析 Action → 环境执行并返回 observation → 更新 Agent History。
  - 终止条件：任务结束或达到最大步长。
- 作用定位：它是 RL 的训练样本单位，后面的 mask、reward、advantage 全部挂在它身上。

### 对应链条第 4 环：Token Mask 区分来源

**Token Mask**
- 一句话本质：给 trajectory 中每个 token 标记「是否由模型自己生成」的开关。
- 结构化拆解：
  - 解决什么问题：trajectory 里混着模型输出和环境输出，若不加区分，模型会被训练去「生成」环境返回的测试结果。
  - 关键机制：调用 BaseTool 时设置对应 token 的 mask；非模型生成的 token 置 0，模型生成的 Agent token 置 1。
  - 只有 mask=1 的部分参与 loss 计算。
  - 环境反馈虽然不参与 loss，但保留在上下文中作为条件。
- 作用定位：这一步决定了训练信号的纯净度，是 Agent RL 与普通 SFT 在数据处理上的关键分界。

### 对应链条第 5–7 环：Reward、PPO 与资源

**Reward 与 verifier**
- 一句话本质：Reward 是任务结束后对整条轨迹给出的数值评价；verifier 是在多个候选中做筛选的判定器。
- 结构化拆解：
  - Reward 在任务结束时计算，作为该条 trajectory 的优化信号。
  - verifier 用于 pass@16：16 个候选经过它选择后得出效果指标。
  - pass@1 与 pass@16 分工：前者只体现 Policy 单次 rollout 的能力，后者同时包含多次采样与 verifier 的贡献。
- 作用定位：reward 是把「任务成败」转成「梯度信号」的唯一通道；两个指标则分别回答「模型本身多强」和「系统整体多强」。

**PPO 与 advantage**
- 一句话本质：PPO 是一种用「相对预期好多少」来约束参数更新幅度的策略优化算法；advantage 就是那个「相对预期好多少」的量化值。
- 结构化拆解：
  - PPO 由 verl 实现，由 rLLM 的训练脚本触发。
  - advantage 的计算受每个 problem 的采样数量、异步执行等参数影响。
  - Policy optimization 依据 advantage 更新 Qwen3-32B 的参数。
- 作用定位：闭环中唯一真正改变模型参数的一步，前面的所有工作都是为它准备输入。

**训练资源分工**
- 一句话本质：GPU 负责模型侧计算，CPU 与容器负责代码侧执行，两者同时发生。
- 结构化拆解：
  - GPU：Qwen3 推理、rollout、reward 计算、Policy 训练、梯度更新。
  - CPU 与容器：Docker image、代码库 checkout、编译、代码搜索、编译测试。
  - 规模：至少 64 张 GPU、并行 512 个 Docker 容器；新配置为 8 节点 × 8 卡。
- 作用定位：说明这条链的成本边界——Agent RL 的瓶颈不只在模型，也在环境的并发执行能力。

---

## 逻辑链回收

- **第 1 环（基座与训练对象）**：已闭环。Qwen3-32B 作为 Policy，不做 Coding Agent SFT 直接 Agent RL，是全文的既定前提。
- **第 2 环（任务与环境）**：已闭环。R2E-Gym 筛选出 4000+ 问题，每个问题对应一个 Docker 环境。
- **第 3 环（环境接入）**：已闭环。SWEEnv 的读数据 → 建环境 → 启 Docker → 多轮操作 → 算 reward → 关环境的流程已完整说明。
- **第 4 环（Rollout 与轨迹）**：已闭环。Agent executor 的循环步骤与终止条件均已给出。
- **第 5 环（Token Mask）**：已闭环。模型 token mask=1 参与 loss、环境 token mask=0 仅作上下文，这是整条链最关键的设计点。
- **第 6 环（Reward 回填）**：**部分开放**。原文只确认「任务结束后算 reward」，但 reward 具体如何写入轨迹、MC Return 如何计算（是否折扣、是否有 baseline）未展开，属于开放问题。
- **第 7 环（PPO 更新）**：已闭环于「脚本调用 verl、参数影响数据生成/advantage/优化」这一层，但具体超参取值与训练步数未给出，属于开放问题。
- **第 8 环（评估与资源）**：已闭环。pass@1 / pass@16 的含义与 64 GPU + 512 容器的规模均已明确。

**尚未闭环的开放问题**：Final Reward 的写入方式与 MC Return 的计算细节；reward 是二值还是部分得分；数据筛选标准；跳过 SFT 的实证依据；verifier 的具体形态；异步执行下的数据新鲜度处理。

## 原文文案

Coding Agent 到底怎么真正跑起来的。那我们来看最后一个组件，就是 DeepSWE。就是我们前面其实已经拆解了这个任务环境、Agent 的 trajectory 和 reward。然后 DeepSWE 就把这些组件真正进入到这种 RL 训练系统里。然后它现在有部分组成，一个是 R2E-Gym，给我们提供 SWE 的一整套 trajectory 的环境。然后 rLLM 负责 Agent 的 trajectory 和训练过程的编排。而 verl 提供的底层分布式是比较核心的训练能力。然后它的 base model 是 Qwen3-32B。首先我们用这个 Qwen3-32B 做一个 base model，对吧？然后公开方案，从这个训练模型出发，直接进行 Agent 的 RL 采用的方案其实没有先进行专门的 Coding Agent 的 SFT，训练数据还是来自于 R2E-Gym，就原始环境经过这个数据筛选，形成了这个 4000 多个训练问题，然后每个问题都可以进入到这个 Docker 环境去执行。所以它整体的训练流程就是 Qwen3，然后再到 R2E-Gym 的 Tasks，然后 Docker 里运行 Agent 的 rollout，然后生成 trajectory，算 reward，然后通过这些训练数据，通过 verl 和 rLLM 来训练这个模型，最后更新 Policy 的这个参数。整体的流程听起来很简单，但是里面的细节还是挺漂亮的。然后 DeepSWE 的这个结果需要去分两个指标，一个是 pass@1，就是 pass@1，这个什么意思，用衡量说单次 Policy rollout 的成功率。第二是 pass@16，它衡量的是说，我 16 个候选经过这种 verifier 选择以后的一个效果。所以两个指标对应的是说，我一个是体现出训练后 Policy 的能力，然后 pass@16 同时包含了这种多次采样以及 verifier 的这种贡献。而 SWEEnv 提供了一个 SWE 环境的封装，就是它把 R2E-Gym 的环境接入到 Agent 的框架里。对吧，它首先先读到这个数据，对吧，把 R2E-Gym 的数据读进去，然后创建一个 SWE 的环境，然后环境内部再创建一个代码的环境，这个任务启动 Docker，然后 Agent 就可以在这个 environment 里面执行多轮的操作了。然后任务结束之后，我就可以算这个 reward，然后把环境关闭，这就是一个代码的过程，其实代码没有几行，很简单。现在我们进入到这个训练阶段里，比较重要的部分，就是 rLLM，rLLM 就是 SWE Agent 的负责这个 Agent 的交互逻辑，然后 Agent 的 executor 就负责组织这种多轮的执行，运行一次，然后它的过程可以拆为这个环境的初始化，然后 Agent 的初始化，构造 Prompt，然后用 Policy，然后解析 Action，然后以及说环境真正执行的 Action，返回 observation，然后更新 Agent 的 History，然后直到说我这个任务结束或者达到这种最大步长，然后每个 Agent 其实都会对应一个独立的 environment，然后训练系统其实可以并行进行很多组 Agent 和这个 environment，这个我们就看了 RL 的一个数据处理，就是我一个 Agent 的 trajectory，其实里面包含两种 token，对吧，一个是我模型生成的 token，一个是我环境反馈的 token，比如说测试结果，或者那种工具结果，等等等等，就是这两种 token 在 RL 中承担不同的作用，首先它会调用 BaseTool，token 的 Mask，就是会设置对应 token 的 Mask，如果它不是模型生成的，我就把它置成 0 Mask，而 Agent token 这个 Mask 就是 1，就是用这部分 token 来更新它的 loss，然后训练之后，这个模型能学习自己生成内容，然后环境反馈，而环境反馈作为一个条件上下文，然后我们看 DeepSWE 训练时使用的是 rLLM 和 verl，这个 rLLM 提供的训练脚本，你就直接执行就可以了，然后这个命令最终会调用 verl 的 PPO 的训练，就是具体可以看一下它的这几个参数，一个是模型、训练数据、验证数据以及学习率，然后 worker 数量、异步执行，或者是每个 problem 的采样数量，等等等等，就像这些参数其实决定我训练数据的生成以及我的 advantage 的一个计算，还有 Policy 的 optimization，我们来看一下这个计算资源，就是它这个训练其实需要很大的训练资源，就是模型的推理和代码环境，它其实是同时来发生的，就 GPU 这边它负责 Qwen3 模型的推理，然后 rollout，然后 reward 的计算，Policy 训练，然后梯度的更新，然后 CPU 和容器里面负责这个 Docker 的 image，然后代码库的 checkout，然后编译、搜索 code，这个编译的测试，支持使用流式的计算，等等等等，然后官方文档说要求至少需要 64 张 GPU，然后并行运行 512 个 Docker container，然后新的配置中说是 8 个节点，然后每个节点有 8 张 GPU，需要的卡还是挺多的，对，64 张 GPU，然后我们最后把整个系列来梳理一下，一个是说它有一个生成任务的模型，还有一个 Docker environment，就提供环境的模块，然后 Coding Agent，再到 trajectory 的处理，再到 reward，再到 rLLM 和 verl 训练的框架，以及测试，这整套训练流水线下来，就是从任务开始到训练，它就结束了。
