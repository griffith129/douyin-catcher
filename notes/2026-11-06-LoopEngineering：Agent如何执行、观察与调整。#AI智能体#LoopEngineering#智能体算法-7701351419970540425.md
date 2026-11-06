---
aweme_id: '7701351419970540425'
title: 'Loop Engineering：Agent如何执行、观察与调整。#AI智能体 #LoopEngineering #智能体算法 #任务规划 #AI学习'
author: Vinci的AI小镇
source_url: https://www.douyin.com/video/7701351419970540425
captured_at: 2026-11-06 17:05
tags:
- douyin
- 知识收藏
---

# Loop Engineering：Agent如何执行、观察与调整。#AI智能体 #LoopEngineering #智能体算法 #任务规划 #AI学习

# Loop Engineering：Agent 如何执行、观察与调整——学习笔记

## 精华版
这份笔记的主线是：单个完美提示的做法把每一步输入都压在人身上；更有效的方式是设计一个自动循环系统，让系统反复给执行者下目标、执行动作、观察结果、按结果调整，直到满足可验证的停止条件。四步循环本身简单，真正需要工程化的是外围：触发器决定何时启动；上下文管理决定每轮让系统看到什么；持久状态记录做过什么、什么有效或失败；工具让系统能操作外部资源；独立检查者减少自检偏差。自动循环仍不能取消人：人要写可验证目标、把“为什么做”的意图写到系统能找到的地方、并阅读输出。否则会出现四类风险：代码没人真正验证、人越来越不理解系统、系统行为违背业务意图、人盲目接受输出。结论是：这套方法的效果来自“循环外围工程化 + 保留人工把关”，不是来自四步循环本身。

## 整体逻辑链条梳理
1. 旧做法是人写一次输入，系统返回一次结果，人再写下一次输入；问题在于每一步都靠人手工构造输入。
2. 新做法把“给任务→执行→检查→再给任务”做成自动循环，减少手工构造输入。
3. 循环必须能停：目标要具体、可验证、有停止条件；否则可能过早宣布完成或无限循环。
4. 四步循环不够：还要决定何时启动，即触发器。
5. 每轮产生信息，必须筛选、压缩或按需提供技能说明，防止注意力被淹没。
6. 循环内要有持久记录，记下做过什么、什么有效或失败，供后续使用。
7. 执行阶段要能操作外部资源，检查阶段最好引入独立执行者，减少自检偏差。
8. 自动化完整后仍要人：写目标、写“为什么做”、读输出；否则出现代码无人验证、理解差距扩大、意图丢失、盲目接受输出。
9. 结论：价值在循环外围的工程化和人工把关，不在四步本身。

## 术语首现讲解
（对应链条第 1-8 环的术语支撑）

| 术语（合并相近项） | 一句话本质 | 结构化拆解 | 作用定位 |
|---|---|---|---|
| Loop Engineering（循环工程）、prompt engineering（提示工程）、prompt、AI agent（智能体）、large language model（大语言模型） | Loop Engineering 是设计系统自动完成“下提示—检查—再提示”的反复过程；prompt engineering 是手工设计单次提示；AI agent 是能接收目标并多步执行的 AI 系统；大语言模型根据输入生成输出；prompt 是给模型或智能体的任务输入与约束。 | • Loop Engineering：含目标、执行、检查、再提示循环；机制是自动迭代到停止条件。<br>• prompt engineering：人写单轮提示；机制是优化输入以改变输出。<br>• AI agent：含模型、指令、工具、状态；机制是执行动作并观察结果。<br>• 大语言模型：含参数与输入输出接口；机制是根据上下文预测输出。<br>• prompt：含任务、约束、上下文、输出要求。 | 本文核心对比：旧方式靠人逐个写提示，新方式把提示与检查循环系统化。 |
| 循环四阶段：目标、行动、观察、调整 | 智能体反复执行的最小闭环。 | • 目标：定义完成条件。<br>• 行动：改变外部状态，如打开文件、改代码。<br>• 观察：读取结果，如测试输出。<br>• 调整：根据结果继续、换方案或停止。 | 解释循环如何运行，以及为什么目标必须可验证。 |
| schedule、hook、cron job | 启动循环的触发器。 | • schedule：按时间触发，例如每晚运行。<br>• cron job：常见定时任务实现。<br>• hook：事件触发，例如文件变化、pull request 打开；常用于安全与质量策略。 | 决定循环何时开始。 |
| context engineering、compaction、progressive disclosure of agent skills | 管理每轮循环让智能体看到的信息。 | • context engineering：选择与组织上下文。<br>• compaction：压缩上下文。<br>• progressive disclosure：按需披露智能体技能说明；技能说明包含重复任务的执行指令。 | 防止上下文堆积导致智能体注意力分散。 |
| spine | 循环内持久状态记录。 | • 可用 Markdown 文件记录做过什么、是否有效。<br>• 后续迭代读取这些信息，判断什么有效、什么失败、什么尚未成功。 | 提供跨轮记忆，指导未来行动。 |
| tool access、MCP、tool calling、API | 让智能体调用外部资源执行动作。 | • tool access：工具权限与接口。<br>• tool calling：智能体发起工具调用。<br>• MCP：Model Context Protocol，工具与上下文接入标准。<br>• API：程序接口。 | 执行代码、访问文件系统、运行终端命令、查询数据库等。 |
| sub-agent | 由主智能体调用的独立检查或协作智能体。 | • 有独立指令与独立上下文。<br>• 可使用不同 AI 模型。<br>• 接收任务并返回结果，可充当检查者和协作执行者。 | 在观察阶段做检查，减少同一智能体自检偏差。 |
| human-in-the-loop | 在自动循环中保留人工写目标、写意图、读输出的环节。 | • 人写可验证目标与停止条件。<br>• 人维护意图说明。<br>• 人阅读并验证输出。 | 防止自动化代码生成的主要风险。 |
| comprehension debt、intent debt、AGENTS.md、cognitive surrender | 自动化代码生成的四类风险与相关概念。 | • comprehension debt：系统总代码量与人类理解程度之间的差距。<br>• intent debt：系统“为什么这样做”未被记录，导致行为偏离目标。<br>• AGENTS.md：存放意图、让智能体可见的文件。<br>• cognitive surrender：人盲目接受循环输出。 | 说明为什么“最少人工”仍必须有人工把关。 |
| unit tests、test suite | 验证代码行为是否符合预期的自动化测试。 | • 单元测试检查小范围代码行为。<br>• 测试套件是一组测试。<br>• 通过或失败提供可验证信号。 | 本文例子中的停止条件来源。 |

## 一句话结论
（对应链条第 9 环）  
Loop Engineering 的核心不是把提示写得更完美，而是把“目标—行动—观察—调整”做成自动循环，并在循环外围补齐触发器、上下文管理、持久状态、工具、独立检查者与人工把关。

## 核心要点
（对应链条第 1-8 环的压缩展开）
1. Loop Engineering 把手工逐个写提示改为设计自动循环系统，让智能体自己反复执行、检查、再提示。
2. 循环四阶段是目标、行动、观察、调整；目标必须具体、可验证并有停止条件。
3. 循环外围需要触发器、上下文工程、持久状态、工具访问和子智能体检查。
4. 上下文会随循环累积，需要用压缩或按需披露技能说明来管理。
5. 子智能体用独立指令、独立上下文，甚至不同模型做检查，降低同一智能体自检偏差。
6. 仍需 human-in-the-loop：人写目标与意图、读输出，防止未验证代码、理解债、意图债和认知投降。

## 关键细节
（对应链条第 2-8 环的事实与例子）
- 例子：结账服务有一批失败的单元测试，目标是让这些测试停止失败。
- 循环过程：目标设为让测试通过；智能体行动，如打开文件、编辑代码；观察测试输出；若测试变绿则处理下一个，若仍红则尝试不同修复。
- 坏目标：“make the checkout faster”没有可测量测试，智能体可能无限循环或只跑一轮就宣布完成。
- 好目标：“stop when every unit test in the checkout suite passes”可验证，智能体知道何时满足。
- 触发器：schedule 可按时间触发，例如每晚跑结账循环，常用 cron job；hook 是事件驱动，例如文件变化或 pull request 打开，开发者常用于安全与质量策略、执行政策。
- 上下文来源包括测试输出、文件内容；上下文会堆积，因此需要 context engineering 选择循环能看到的部分。
- 上下文管理手段包括 compaction 压缩上下文，以及 progressive disclosure of agent skills 按需披露重复任务的技能说明。
- spine 可用 Markdown 文件记录智能体做了什么、是否有效，供未来迭代判断什么有效、什么失败、什么尚未成功。
- 行动阶段可通过 tool access 调用外部资源；可用 MCP 或直接 API 做 tool calling；工具用于执行代码、访问文件系统、运行终端命令、查询数据库等。
- 观察阶段可引入第二个智能体作为 sub-agent，充当检查者和协作执行者；它有独立指令、独立上下文，并可能由不同 AI 模型驱动。
- 人工职责：写带停止条件的目标；把意图写到智能体可找到的地方，例如 AGENTS.md；阅读并验证智能体输出。
- comprehension debt 指系统总代码量与人类理解程度之间的差距；智能体写大量代码而人检查较少时，该差距会快速上升，影响紧急生产故障处理。
- intent debt 指系统“为什么这样做”未被记录；智能体可能做出技术上正确但违背项目目标的修改。
- 例子：智能体通过放宽折扣码验证让失败测试通过；测试上成立，但损害业务底线。
- cognitive surrender 指人盲目接受循环输出，认为“AI 做的肯定对”；这会让理解债继续上升。
- 原文强调 “minimal human intervention” 是特定量，不是零：人仍要写目标、写意图、读输出。

## 原文没有讲清的问题
（对应链条第 9 环后的开放问题）
- 如何为不可自动测试的任务设计可验证的停止条件？
- comprehension debt 和 intent debt 应该如何度量、监控和设阈值？
- 上下文压缩与按需披露技能说明的具体策略、触发条件和取舍标准是什么？
- 多个子智能体或不同模型之间如何分工、裁决冲突并保证结果一致？
- 人工审阅如何规模化：应审阅哪些代码、输出和决策点？
- AGENTS.md 由谁维护、多久更新、如何保证智能体始终看到最新意图？
- schedule 与 hook 如何选择，工具权限如何最小化并审计？
- 如何检测和降低 cognitive surrender，而不只是提醒人“要认真看”？

## 逻辑链回收
（逐环回收）
1. 旧做法的问题已闭环：手工提示依赖人逐步构造输入。
2. 新做法已闭环：用自动循环替代手工逐步提示。
3. 目标问题已闭环：目标必须有可验证停止条件，否则循环可能失控。
4. 触发器已闭环：schedule、hook、cron job 决定循环何时启动。
5. 上下文问题已闭环：context engineering、compaction、progressive disclosure 管理每轮可见信息。
6. 持久状态已闭环：spine 记录历史结果，指导后续迭代。
7. 工具与检查已闭环：tool access、MCP、API 支持行动；sub-agent 支持独立检查。
8. 人工环节已闭环：human-in-the-loop 对应四类风险，说明“最少人工”不是零人工。
9. 总体结论已闭环：Loop Engineering 的价值在循环外围工程化与人工把关。

尚未闭环的开放问题：非可测目标的停止条件设计、理解债与意图债的度量、人工审阅的规模化方法，原文均未展开。

## 原文文案

Loop Engineering is a term that's related to working with AI agents, and it's kind of like the newer evolution of prompt engineering. But with prompt engineering, that's all about writing the one perfect, ultimate prompt, and then sending that prompt to a large language model. Then the model comes back with a response, and you need to write the next perfect prompt, and so forth. Now loop engineering is the practice of designing a system that does all that prompting work for you. So what loop engineering does is it takes a prompt and sends it to an AI agent. Then loop engineering checks the agent's work, and prompts it again to go back and forth, back and forth like this, looping until we're done. But we're not having to manually engineer every prompt. That's the job of loop engineering. There's minimal human intervention, although I'll be coming back to the word minimal a bit later. Anyway, let's give an agent a job. Let's say there is a checkout service with a bunch of failing unit tests, and the job is to get the failing unit tests to stop failing. So for that, we're going to use a loop. Now the loop starts with a goal. In this case, get the checkout unit tests to pass. Now the AI agent takes an action. That's the next stage in the loop. And for a coding agent, that's something like maybe opening a file or editing some code. Then the next stage in the loop is the agent observes the output. And the last step in the loop is to adjust based upon that. So if the test went green, yeah, that one's done. It moves on to the next failing one. And if the test is still red, then they would try a different fix. And then it kind of goes back around to the goal. Are we done yet? Nope. Okay, go again. And we keep going around the loop. So specifying a good goal is quite important because the goal is going to get evaluated every time the agent goes around the loop. It's what decides whether the agent keeps going. So a goal of "make the checkout faster" is a pretty bad goal, in much the same way that "be happier" is a pretty bad New Year's resolution. They both have no measurable test. So the agent could go around forever or it could stop after just one pass and declare victory. Whereas a goal of "stop when every unit test in the checkout suite passes" is verifiable. The agent will know for sure when it's met. A good goal is specific, with an end condition, a stopping condition. So that's the loop. Basically, these four stages, not much to it, huh? Doesn't really seem like we need a whole engineering discipline named after it. So why do we? Well, loop engineering is really what gets built around this loop. So let's take a look at that. So something has to kick this loop off. Now, something that might kick it off is a schedule, or something that could kick it off is called a hook. So a schedule is just something simple like "run the checkout loop every night." And a lot of teams would do that with just like a plain old cron job. And then a hook is an event-driven mechanism; the hook is invoked when something specific happens, like a file changing or a pull request opening. Developers largely use hooks for security and quality, such as to enforce policies. Now every trip around the agentic loop is going to generate something. It's going to generate context. Stuff like test output would be context, or file contents, and context can really start piling up, which can make it hard for an agent to focus its attention on the important stuff. So another engineering discipline, context engineering, is choosing which part actually the loop gets to see. Now that could mean that we need to do some operations on this context like compact it. So compaction would be one thing we can do, or we could use the progressive disclosure of agent skills, which contain instructions for how to do a particular recurring job. Now, inside the loop is something that I'm going to call a spine, and this is really persistent state. So maybe that's some Markdown files where the agent writes down what it did and whether it worked, and the information stored in the spine can inform future iterations of the loop on what to do, what works, what failed, and maybe what hasn't worked. Now for this stage here, the action stage, the agent might need to call out to external resources, so it would do that using tool access. Now that might be using standards like MCP, the Model Context Protocol, or maybe we do tool calling directly with APIs. Agents use tools to execute code, to access file systems, to run commands in the terminal, to query databases, all sorts of stuff. The observe stage: rather than have the same agent that wrote the code check the code, good loop engineering brings in a second agent. We can think of that second agent as being a sub-agent, and that kind of acts as a checker and a co-worker to farm tasks out to, and the sub-agent has its own instructions and its own context. And it may be powered by a different AI model than the main AI agent before sending its results back again. So that's the loop. There's a trigger to start the loop, there's context and skills to feed information, there's a spine to remember what happened, there are tools to let it act on tasks, and there are sub-agents to verify the result. Which still leaves the question of what the human is doing while all of this is looping away. Alright, so back to minimal human involvement, because I said loop engineering requires minimal human involvement compared to prompt engineering, because an agent writes its own prompts rather than having a person submit them manually. But even a well-built loop with a checker and a sub-agent and a spine and all the rest of that, it still needs human involvement. A human-in-the-loop approach helps avoid the most dangerous pitfalls that can happen with automated code generation. And which pitfalls am I talking about? Well, I've got four for you, starting with unverified code. So a checker sub-agent is still just an agent. Human developers are ultimately responsible for all shipped code, and that means a real person has to read and verify that code. And the gap between the total amount of code in a system and the degree to which humans understand it is known as comprehension debt. As agents write more code and humans check less of it, our comprehension debt is going to keep going up, and it can build up pretty fast because, well, agents write a lot of code. And if left unmitigated, comprehension debt can be a big problem when human developers need to address urgent production failures. And there's another debt as well that we can put under pitfalls, and that is intent debt. An agent can read what a system does, but working out why the system does it can be a bit harder unless that something has been written down somewhere, perhaps in an AGENTS.md file. Without that, an agent can make a change that is technically sound but goes against a project's objectives. So in our checkout loop example, maybe the agent fixes a failing test by, let's say, relaxing the validation on a discount code, which is a perfectly good fix as far as the tests are concerned but a perfectly bad one as far as the business's bottom line is concerned. So the human's job here is to write the intent down, keep it up to date, and keep it visible to the agent. And then just a fourth pitfall that I want to mention is the rather severe-sounding cognitive surrender. Yeah, we definitely don't want that, but it's very easy to do. Offloading work can lead to cognitive surrender when a person just blindly accepts whatever came out of the loop: "So if the AI did it, I'm sure it's right." Yeah, when that happens, comprehension debt is also going to go up, because now nobody is even trying to understand the generated output. So minimal human intervention turns out to be quite a specific amount of human intervention. So the human, they need to write the goal with the stopping condition. The human needs to write the intent where the agent can find it. And the human needs to read the output from the agent. Loop engineering works best when there's a human in that loop. Are you engineering agentic loops in your own work? Let me know in the comments.
