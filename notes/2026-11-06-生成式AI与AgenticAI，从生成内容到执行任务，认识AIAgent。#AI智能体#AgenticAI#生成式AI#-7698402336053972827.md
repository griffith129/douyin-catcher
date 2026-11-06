---
aweme_id: '7698402336053972827'
title: '生成式AI与Agentic AI，从生成内容到执行任务，认识AI Agent。#AI智能体 #AgenticAI #生成式AI #AI学习 #人工智能大模型'
author: Vinci的AI小镇
source_url: https://www.douyin.com/video/7698402336053972827
captured_at: 2026-11-06 16:58
tags:
- douyin
- 知识收藏
---

# 生成式AI与Agentic AI，从生成内容到执行任务，认识AI Agent。#AI智能体 #AgenticAI #生成式AI #AI学习 #人工智能大模型

# 生成式AI与Agentic AI学习笔记

## 精华版

**生成式AI**  
1. 一句话本质：生成式AI是一类根据用户请求、基于训练中学到的统计关系生成内容的系统。  
2. 结构化拆解：它解决内容生成问题；关键机制是反应式等待用户请求，根据训练模式预测并生成文本、图像、代码或音频，工作止于生成，不自行继续行动。  
3. 作用定位：它是本文档的对比起点，用于界定“只生成内容、不继续执行任务”的AI。

**Agentic AI / AI Agent**  
1. 一句话本质：Agentic AI是一类以目标为导向、能在最少人工干预下连续采取行动的系统；AI Agent是这类系统的具体执行实体。  
2. 结构化拆解：它解决持续管理和多步流程问题；关键机制是感知环境→决定行动→执行行动→从输出学习→循环；与生成式AI不同，它不把工作止于生成。  
3. 作用定位：它是本文档的第二类AI，用于说明AI从内容生成走向任务执行。

**LLM**  
1. 一句话本质：LLM是经大规模文本训练、能根据上下文预测并生成语言序列的模型。  
2. 结构化拆解：它解决语言理解与生成问题；关键机制是从大量数据学习统计关系，根据上下文逐步预测下一个词或片段；在本文档中，它既是对话式工具的骨干，也为Agentic系统提供推理能力。  
3. 作用定位：它是生成式AI与Agentic AI常共享的底层基础，理解它才能理解Agentic AI为何能进行推理和规划。

浓缩主线：生成式AI是反应式系统，收到用户请求后生成内容，工作止于生成；Agentic AI是主动式系统，常从用户请求出发，通过“感知—决策—执行—学习”循环追求目标，最少人工干预。两者常共享LLM基础，图像音频等生成还使用其他专门模型。生成式AI适合内容创作，但人类需要审核和策展；Agentic AI适合持续管理和多步流程，例如个人购物代理。Agentic AI可用逐步推理把复杂任务拆成逻辑步骤。未来最强系统不是纯生成或纯Agentic，而是能判断何时生成探索、何时行动承诺的智能协作者。

## 整体逻辑链条梳理

1. 区分两类AI：生成式AI是反应式系统，等待用户发起请求；这个请求在原文中称为prompt（提示词）。为什么成立：原文以“生成后是否继续行动”作为分界。衔接：先定义差异，才能讨论共同基础与应用。  
   **prompt**  
   1. 一句话本质：prompt是用户发给生成式AI或Agentic系统的输入指令，用来指定希望完成的任务或生成的内容。  
   2. 结构化拆解：它解决“把用户意图传给系统”的问题；关键机制是系统读取prompt后决定生成内容或启动目标追求；在生成式AI中通常决定一次性输出，在Agentic AI中可作为多步行动的起点。  
   3. 作用定位：它是本文档中两类AI的共同输入形式，掌握它才能理解生成式AI的触发方式和Agentic AI的任务起点。

2. 共同基础：两类AI常共享LLM基础；LLM为Agentic系统提供推理能力，图像音频等生成还使用其他专门模型。为什么成立：原文明确说LLM是对话式工具的骨干，也为Agentic系统提供推理能力。衔接：有了底层模型，才能解释Agentic AI如何推理。  
   **LLM**已在精华版讲解，后文直接使用。

3. 生成式AI应用：内容创作需要人类审核与策展。为什么成立：原文用视频创作者例子说明AI生成脚本意见、缩略图概念和背景音乐，人类逐项审核、修正并导演全过程。衔接：这说明生成式AI的边界与人类角色。

4. Agentic AI应用：多步持续管理场景更适合Agentic AI。为什么成立：原文用个人购物代理说明它可查可用性、监控价格、处理结账、协调配送。衔接：从应用引出其实现机制。

5. 实现机制：Agentic AI可用chain of thought reasoning把复杂任务拆成较小逻辑步骤。为什么成立：原文用组织会议例子展示Agent先理解规模、时长、预算，再研究场地、检查可用性。衔接：这解释Agent如何做决策。  
   **chain of thought reasoning**  
   1. 一句话本质：chain of thought reasoning是让模型把复杂任务拆成多个较小逻辑步骤并逐步推导的推理方法。  
   2. 结构化拆解：它解决复杂任务一次性处理困难的问题；关键机制是模型生成内部推理步骤或内部对话，再据此选择行动；在本文档中用于说明Agentic AI如何规划与决策。  
   3. 作用定位：它是连接LLM推理能力与Agentic AI任务执行的机制，掌握它才能理解Agent如何把目标拆成可执行步骤。

6. 未来趋势：最强系统不是纯生成或纯Agentic，而是智能协作者，能判断何时生成探索、何时行动承诺。为什么成立：原文结论指出未来系统会理解两种模式的切换。衔接：回收差异、基础、应用与机制，形成闭环。

## 一句话结论

对应链条第1—6环的结论是：生成式AI是等待用户请求后生成内容的反应式系统，Agentic AI在底层模型推理能力上主动执行多步任务，未来趋势是二者结合为能判断何时生成、何时行动的智能协作者。

## 核心要点

对应链条第1—6环，核心要点如下。

1. 生成式AI是反应式系统，收到prompt后基于训练模式生成文本、图像、代码或音频，生成后不自行继续行动。
2. Agentic AI是主动式系统，常从用户请求出发，通过感知环境、决定行动、执行行动、从输出学习并循环来追求目标。
3. 两者常共享LLM基础：LLM是对话式工具的骨干，也为Agentic系统提供推理能力；图像音频等生成还使用其他专门模型。
4. 生成式AI适合内容创作，但人类需要审核、修正和策展AI生成的候选内容。
5. Agentic AI适合持续管理和多步流程，例如个人购物代理可查可用性、监控价格、处理结账和协调配送。
6. Agentic AI可用chain of thought reasoning把复杂任务拆成较小逻辑步骤；未来最强系统是混合生成与行动能力的智能协作者。

## 关键细节

对应链条第2—5环，关键细节如下。

- 视频提到图像和音频生成通常使用扩散模型。  
  **扩散模型**  
  1. 一句话本质：扩散模型是一类通过学习从噪声逐步还原数据的过程来生成图像或音频的模型。  
  2. 结构化拆解：它解决图像、音频等非文本内容生成问题；关键机制是训练时学习加噪与去噪的统计规律，生成时从噪声开始逐步还原；与LLM分工不同，LLM主要处理语言，扩散模型常用于图像音频。  
  3. 作用定位：它说明生成式AI不只有LLM基础，不同生成任务依赖不同模型；理解它有助于区分文本生成与图像音频生成的底层技术。

- 生成式AI是反应式系统：等待prompt，工作止于生成；原文称其为“模式匹配机器”，学习词、像素、声波之间的统计关系。
- Agentic AI的生命周期：感知环境→决定行动→执行行动→从输出学习→循环，且最少人工干预。
- LLM既作为对话式工具的骨干，也为Agentic系统提供推理能力。
- 内容创作例子：视频创作者可用生成式AI审脚本、建议缩略图概念、生成背景音乐；但每一步都有人类审核、修正和策展。
- 个人购物代理例子：给定商品输入后，主动查平台可用性、监控价格波动、处理结账、协调配送，必要时才请求用户输入。
- chain of thought reasoning例子：组织会议时，Agent先理解会议规模、时长、预算，再研究匹配场地、检查可用性等，通过内部对话探索问题空间。
- 未来判断：最强AI系统不会纯粹生成或纯粹Agentic，而是智能协作者，知道何时生成探索、何时行动承诺。
- 数据：视频未给出具体数据。

## 原文没有讲清的问题

对应链条第5—6环的开放延伸如下。

- Agentic AI如何“感知环境”？感知哪些数据源、权限边界和状态信息？
- LLM具体如何为Agentic系统提供推理能力？chain of thought reasoning的可靠性如何验证？
- Agentic AI在多步执行中如何处理错误、权限控制、安全审计和人类接管？
- 个人购物代理如何处理支付、隐私、平台规则和失败回滚？
- 生成式AI与Agentic AI在系统架构上如何衔接？何时调用生成、何时调用行动？
- 未来“智能协作者”如何判断从探索转向承诺行动的标准？
- 扩散模型与LLM在同一系统中如何协作，原文未展开。

## 逻辑链回收

对照链条第1—6环逐环回收如下。

1. 第1环已闭环：生成式AI是反应式，Agentic AI是主动式，差异成立。
2. 第2环部分闭环：LLM作为共同基础和推理来源已说明；但LLM与扩散模型等专门模型的统一协作机制未展开，属于开放问题。
3. 第3环已闭环：生成式AI适合内容创作，但需要人类审核与策展。
4. 第4环部分闭环：Agentic AI适合多步流程，购物代理例子成立；但支付、隐私、权限和异常处理未讲清，属于开放问题。
5. 第5环部分闭环：chain of thought reasoning可解释Agent的规划与决策；但其可靠性和验证方式未讲清，属于开放问题。
6. 第6环部分闭环：未来趋势指向混合生成与行动能力的智能协作者；但“何时生成、何时行动”的判断标准未展开，属于开放问题。

## 原文文案

What's the difference between generative AI and agentic AI? Well, they're two distinct approaches to artificial intelligence. And I think we're all familiar with generative AI, things like chatbots and image generators and the like, and they are really fundamentally reactive systems. They wait for you to do something. Specifically, they wait for you to prompt them. And once you prompt them, their job is to generate some kind of content based upon what you provided in the prompt, and they're using patterns learned during training. Now, the things that it can generate, well, that might be some text, or it might be an image, or it might be a piece of code, or it might be some audio. These are all sorts of things that we can generate with generative AI, and they're essentially sophisticated pattern matching machines. So they've learned the statistical relationships between words and between pixels and between sound waves, and they've learned that from massive data sets. So when you provide a prompt, generative AI predicts what comes next based on its training. But its work does end at generation. It doesn't take further steps without your input. Now, agentic AI systems, by contrast, those are not reactive. They are proactive systems. Now, like generative AI, they often start with a user prompt. But that prompt is then used to pursue goals through a series of actions. And an agentic system basically goes through a bit of a life cycle. So the way this works is it kind of, first of all, perceives its environment, if you like. And then once it's done that, it can decide an action to take. Once it's decided that action, it can then execute that action. And then once that action has been executed, it can kind of learn from the output, and then round, around we go, all with minimal human intervention. Now, both of these AI approaches often share a common foundation. And that common foundation is large language models, or LLMs. LLMs serve as the backbone for chatbots, and yet there's actually other tools that are used for some of these other generative things, diffusion models typically for images and audio. But the chatbots use LLMs, and LLMs also provide the reasoning engine that powers agentic systems. But before we go any deeper into that, let's talk about some real world applications and use cases. Now, maybe this doesn't put me in the best light, but I don't think I'm the only one using generative AI to help with the task of content creation and especially creative content creation. Now, before work this morning, and this is completely true, I use the chatbots to help write the next chapter of my Nelson DeMille fan fiction novel. And right now, you're probably thinking how profoundly cool and absolutely non-nerdy this guy is, but for many of us, GenAI does help with daily tasks. Like, let's consider how a YouTuber might use a generative AI system to review scripts and suggest thumbnail concepts and maybe even generate background music. But at each step there is a human, there is a human creator, and that human creator is looking at this generated content and they are reviewing it. Check it's what they want, probably isn't, so then they are refining it as well, and they are really going through and directing this whole process. The AI generates possibilities, but the human curates them. Now, agentic AI that kind of thrives in scenarios that require ongoing management and consist of multi-step processes, so not just one thing at a time. So consider a personal shopping agent. Given a product to purchase as input, it actively hunts for availability across platforms, it might monitor price fluctuations, it might handle checkout processes and it might even coordinate delivery. Largely by itself, seeking input only from you, only when it's needed. But how does it do that? Well, it turns out that the LLMs that are behind much of generative AI can also be used to provide reasoning capabilities to AI agents. So, this essentially here we're using GenAI's ability to kind of think in inverted commas there, and it's thinking through problems. And this has a name, it's called chain of thought reasoning, and this is what LLMs are so very good at. It's a process where the agent basically breaks down a complex task into smaller logical steps, kind of like how humans tackle difficult problems as well. So, let's imagine one, let's imagine that we want to have an agent that is planning a complex task like organizing a conference. So, what it's going to do is it's going to use GenAI to generate an internal dialogue, and that dialogue might go something like this. It might say, first I need to understand the conference requirements: the size, the duration, the budget, that sort of thing. Then I should research available venues, matching those parameters, then it might think, well, for those venues that meet those requirements and I need to check availability, and so on. It's effectively the agent really kind of talking to itself to explore the problem space before taking action. GenAI is basically the cognitive engine driving an agent's decision making. Now, looking ahead, the most powerful AI systems probably won't be purely generative or purely agentic, they're going to be intelligent collaborators. They'll understand when to explore options through generation, and when to commit to courses of action through agentic action. Like an agent, it would know when to generate the next chapter of fan fiction, so it's ready after a video shoot. Maybe it's ready right now.
