from __future__ import annotations

import os
from datetime import date

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilyExtract, TavilySearch

from .config import Settings


SYSTEM_PROMPT = """你是一个严谨的 AI native product 研究 agent。

任务：自动联网发现一个近期热门 AI native product，并基于公开资料写中文 Markdown 深度使用报告。

约束：
- 只选择 1 个产品。
- 优先选择最近 7-30 天被发布、讨论、评测或更新的产品。
- AI 必须是产品核心工作流，而不是普通软件里的边缘 AI 功能。
- 不要声称你已经注册、登录、购买、上传私有数据或真实操作了产品。
- 所有结论必须能从公开网页、文档、演示、博客、发布页或第三方评价中得到支持。
- 报告中必须包含来源链接。

输出必须是 Markdown，且只输出 Markdown。
"""


USER_PROMPT_TEMPLATE = """请完成一次 AI native product 公开研究报告。

参数：
- 当前日期：{today}
- 时间窗口：最近 {days} 天
- 候选上限：{max_candidates}
- 搜索主题：{topic}

执行步骤：
1. 搜索近期热门的 AI native product 候选，搜索词可以包括英文关键词。
2. 从候选里选择 1 个最值得深度分析且公开资料较完整的产品。
3. 抽取官网、发布页、文档、博客、评测或讨论页中的公开信息。
4. 生成中文 Markdown 报告。

报告结构必须包含：
# 产品名：一句话定位

## 基本信息
- 产品：
- 官网：
- 发现来源：
- 最近信号：
- 置信度：

## 一句话定位

## 目标用户

## 核心使用场景

## 典型上手路径

## AI Native 特征

## 产品亮点

## 限制和风险

## 适合谁 / 不适合谁

## 结论评分
给出 1-10 分，并解释评分。

## 参考来源
列出可点击链接。

请在报告开头明确说明：本报告基于公开资料，不代表已经完成真实账号试用。
"""


class AIProductAgent:
    def __init__(self, settings: Settings) -> None:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
        self.model = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=90,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self.tools = [
            TavilySearch(max_results=5, topic="general"),
            TavilyExtract(),
        ]
        self.agent = create_agent(
            self.model,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )

    def run(
        self,
        *,
        days: int,
        topic: str,
        max_candidates: int,
        today: date | None = None,
    ) -> str:
        report_date = today or date.today()
        prompt = USER_PROMPT_TEMPLATE.format(
            today=report_date.isoformat(),
            days=days,
            topic=topic,
            max_candidates=max_candidates,
        )
        result = self.agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("Agent returned no messages.")
        content = getattr(messages[-1], "content", None)
        if not content:
            raise RuntimeError("Agent returned an empty report.")
        if isinstance(content, list):
            return "\n".join(str(part) for part in content)
        return str(content)
