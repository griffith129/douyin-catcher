---
aweme_id: '7698402336053972827'
title: '生成式AI与Agentic AI，从生成内容到执行任务，认识AI Agent。#AI智能体 #AgenticAI #生成式AI #AI学习 #人工智能大模型'
author: Vinci的AI小镇
source_url: https://www.douyin.com/video/7698402336053972827
captured_at: 2026-11-03 17:27
tags:
- douyin
- 知识收藏
---

# 生成式AI与Agentic AI，从生成内容到执行任务，认识AI Agent。#AI智能体 #AgenticAI #生成式AI #AI学习 #人工智能大模型

## 一句话结论
生成式AI是等待提示、只负责生成内容的被动系统，而Agentic AI是能围绕目标自主感知、决策、执行并从结果中学习的主动系统，二者常共享大语言模型这一基础。

## 核心要点
- 生成式AI是反应式系统，必须由用户提示触发，任务在生成内容后即结束。
- 生成式AI本质是 sophisticated pattern matching machines，基于训练数据预测“接下来应该是什么”。
- Agentic AI是主动式系统，虽常以用户提示为起点，但会通过一系列动作追求目标，且只需极少人工干预。
- Agentic AI的运行循环可概括为：感知环境→决定行动→执行行动→从输出中学习，然后循环。
- 生成式AI与Agentic AI常共享大语言模型基础：LLM既是聊天机器人的 backbone，也为智能体提供推理引擎。
- 二者适用场景不同：生成式AI适合需要人类持续管理和多步审校的任务，Agentic AI适合需要持续管理、多步骤推进的场景（如个人购物代理）。

## 关键细节
- 生成式AI可生成的内容包括文本、图像、代码、音频等。
- 图像和音频等生成任务常用扩散模型（diffusion models），聊天机器人则使用LLM。
- Agentic AI使用LLM进行“chain of thought reasoning”，把复杂任务拆成更小的逻辑步骤。
- 视频举例：个人购物代理可根据“购买某产品”的输入，主动跨平台查找库存、监控价格波动、处理结账并协调配送，只在需要时向用户寻求输入。
- 视频举例：组织会议时，智能体可生成内部对话，先理解会议需求（规模、时长、预算），再研究匹配的场地，再检查可用性，相当于在行动前“自言自语”探索问题空间。
- 视频举例：YouTuber可用生成式AI审阅脚本、建议缩略图概念、生成背景音乐，但每一步都有人类创作者审核、修正和导演整个过程。
- 视频观点：未来最强大的AI系统可能既不是纯生成式也不是纯Agentic，而是“intelligent collaborators”，知道何时通过生成探索选项、何时通过Agentic行动承诺执行。

## 原文没有讲清的问题
- Agentic AI“从输出中学习”具体如何实现、学习发生在模型层面还是工作流层面，视频未展开。
- Agentic AI在跨平台购物、协调配送等场景中如何获得系统权限、如何处理支付与安全风险，视频未说明。
- chain of thought reasoning在智能体中如何被触发、如何与外部工具调用衔接，视频只给了概念性例子。
- “minimal human intervention”中人类干预的边界和触发条件是什么，视频未明确。
- 生成式AI与Agentic AI共享LLM基础时，二者在架构上的具体差异（如工具调用、记忆、规划模块）未展开。

## 原文文案

What's the difference between generative AI and agentic AI? Well, they're two distinct approaches to artificial intelligence. And I think we're all familiar with generative AI, things like chatbots and image generators and the like. And they are really fundamentally reactive systems. They wait for you to do something. Specifically, they wait for you to prompt them. And once you prompt them, their job is to generate some kind of content based upon what you provided in the prompt. And they're using pansy learned during training. Now, the things that it can generate, well, that might be some text or it might be an image or it might be a piece of code or it might be some audio. These are all sorts of things that we can generate with generative AI. And they're essentially sophisticated pattern matching machines. They've learned the statistical relationships between words and between pixels and between sound waves. And they've learned that from massive data sets. So when you provide a prompt, Genei predicts what should come next based on its training. But it's work does end at generation. It doesn't take further steps without your input. Now, agentic AI systems by contrast, those are not reactive. They are pro active systems. Now, like generative AI, they often start with a user prompt. But that prompt is then used to pursue goals through a series of actions. And an agentic system basically goes through a bit of a life cycle. So the way this works is it kind of, first of all perceives, perceives its environment, if you like. And then once it's done that, it can decide an action to take. Once it's decided that action, it can then execute that action. And then once that action has been executed, it can kind of learn from the output. And then round around we go all with minimal human intervention. Now, both of these AI approaches, often share a common foundation. And that common foundation is large language models or LLMs. LLMs serve as the backbone for chat bots. And yet there's actually other tools that are used for some of these other generative things, diffusion models typically for images and audio. But the chat bots we use LLMs and LLMs also provide the reasoning engine that powers agentic systems. But before we go any deeper into that, let's talk about some real world applications and use cases. Now, maybe this doesn't put me in the best of lights, but I don't think I'm the only one using generative AI to help with the task of content creation and especially creative content creation. Now, before work this morning and this is completely true, I use the chat bot to help write the next chapter of my Nelson Demille fan fiction novel. And right now you're probably thinking how profoundly cool and absolutely non-nerdy this guy is. But for many of us, Gen AI does help with daily tasks. Like, let's consider how a YouTuber might use a generative AI system to review scripts and suggest thumbnail concepts and maybe even generate background music. But at each step, there is a human. There is a human creator. And that human creator is looking at this generated content and they are reviewing it. Check it's what they want. Probably isn't. So then they are refining it as well. And they are really going through and directing this whole process. The AI generates possibilities, but the human curates them. Now, a genetic AI that kind of thrives in scenarios that require ongoing management and consists of multi-step processes. So not just one thing at a time. So consider a personal shopping agent. Given a product to purchase as input, it actively hunts for availability across platforms. It might monitor price fluctuations. It might handle checkout processes and it might even coordinate delivery. Largely by itself, seeking input only from you only when it's needed. But how does it do that? Well, it turns out that the LLMs that are behind much a generative AI can also be used to provide reasoning capabilities to AI agents. So this essentially here we're using Genai's ability to kind of think in inverted commas there and it's thinking through problems. And this has a name. It's called chain of thought reasoning. And this is what LLMs are so very good. It's a process where the agent basically breaks down a complex task into smaller logical steps kind of like how humans tackle difficult problems as well. So let's imagine one. Let's imagine that we want to have an agent that is planning a complex task like organizing a conference. So what it's going to do is it's going to use Genai to generate an internal dialogue. And that dialogue might go something like this. It might say first I need to understand the conference requirements at the side, the duration, the budget, that sort of thing. Then I should research available venues matching those parameters. Then it might think, well, for those venues that meet those requirements and I need to check availability and so on. It's effectively the agent really kind of talking to itself to explore the problem space before taking action. Genai is basically the cognitive engine driving an agent's decision making. Now looking ahead, the most powerful AI system is probably won't be purely generative or purely agentic. They're going to be intelligent collaborators. They'll understand when to explore options through generation and when to commit to courses of action through agentic action. Like an agent that would know when to generate the next chapter of fan fiction. So it's ready after what a video shoot. Maybe it's ready right now.
