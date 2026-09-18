"""进阶 12：观察自动摘要触发后，原始对话保存在哪里。
运行：.venv/bin/python lessons/ch03/code/advanced/12_summarization.py
无需 API Key。固定模型只验证归档机制，不验证摘要质量。
"""


def main():
    from deepagents import create_deep_agent
    from deepagents.backends import StateBackend
    from langgraph.checkpoint.memory import InMemorySaver
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from deepagents.middleware.summarization import SummarizationMiddleware


    # 用固定回复代替付费模型：本实验只看“是否归档”，不评价摘要的好坏。
    class FixedReplyModel(BaseChatModel):
        reply: str = "已收到本轮消息。"

        @property
        def _llm_type(self):
            return "ch03-fixed-reply"

        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            # 按 LangChain 要求把一条 AIMessage 包装为模型返回结果。
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])


    backend = StateBackend()
    summary_model = FixedReplyModel(reply="实验摘要：继续收集证据；历史原文见归档文件。")
    agent = create_deep_agent(
        model=FixedReplyModel(),
        backend=backend,
        checkpointer=InMemorySaver(),
        middleware=[SummarizationMiddleware(
            model=summary_model,
            backend=backend,
            trigger=("messages", 6),  # 用消息数量触发，不必构造很大的文本。
            keep=("messages", 2),     # 保留近期消息，较早内容由摘要机制处理。
        )],
    )
    config = {"configurable": {"thread_id": "summary-lab"}}
    # 使用较小的消息数阈值，八轮简单对话就能观察归档，不需要构造海量内容。
    for i in range(8):
        result = agent.invoke(
            {"messages": [HumanMessage(content=f"ORIGINAL-{i}: 本轮证据及约束。")]},
            config=config,
        )
    # StateBackend 的归档文件从 files 字段检查，不能到磁盘上寻找这个虚拟路径。
    archives = {
        path: data for path, data in result.get("files", {}).items()
        if path.startswith("/conversation_history/") and path.endswith(".md")
    }
    assert archives, "没有生成归档，应检查摘要触发条件"
    archive_text = "\n".join(data["content"] for data in archives.values())
    assert "ORIGINAL-0" in archive_text
    assert result["messages"][-1].content == "已收到本轮消息。"
    print("归档文件：", list(archives))
    print("PASS: 自动摘要触发，早期消息归档，后续调用继续执行")


if __name__ == "__main__":
    main()
