"""实验 08（选学）：工具返回太长时，完整正文会去哪里？

运行：.venv/bin/python lessons/ch03/code/08_large_result.py
无需 API Key。框架测试模型只负责固定调用一次工具，不承担推理。
建议先完成 01–06，再看本实验的 Agent 中间件部分。
"""

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool


class FixedToolModel(FakeMessagesListChatModel):
    # 测试模型已经由库实现。这个方法告诉 Agent：可以接受工具绑定。
    # 真实模型会思考“用什么工具”；本实验直接按下面的 responses 顺序播放。
    def bind_tools(self, tools, **kwargs):
        return self


def main():
    # 用几百行材料触发卸载，而不是为演示而请求一个昂贵的真实模型。
    original = "\n".join(f"row-{i}: " + "example material " * 5 for i in range(500))

    @tool
    def get_material() -> str:
        """返回一份很长的实验资料。"""
        return original

    model = FixedToolModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "get_material", "args": {}, "id": "large-material",
        }]),
        AIMessage(content="工具调用完成。"),
    ])
    backend = StateBackend()
    agent = create_deep_agent(
        model=model,
        tools=[get_material],
        backend=backend,
        # 当前版本允许同名中间件替换默认实例；用较小阈值方便观察。
        # 这条路径按字符数近似 token，并非精确 tokenizer 计数。
        middleware=[FilesystemMiddleware(backend=backend, tool_token_limit_before_evict=1000)],
    )
    result = agent.invoke({"messages": [{"role": "user", "content": "获取实验资料。"}]})
    tool_reply = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    print("\n① 原始工具返回字符数：", len(original))
    print("② 实际 ToolMessage 字符数：", len(tool_reply.content))
    print("③ ToolMessage 开头：\n", tool_reply.content[:300])

    # 这次使用 StateBackend，所以保存的文件在结果的 files 中，不在电脑磁盘里。
    saved = {p: data for p, data in result["files"].items() if p.startswith("/large_tool_results/")}
    assert len(saved) == 1
    saved_path, saved_data = next(iter(saved.items()))
    assert saved_data["content"] == original
    assert saved_path in tool_reply.content
    assert len(tool_reply.content) < len(original)
    print("\n④ 文件保存到：", saved_path)
    print("⑤ 文件内容与原始工具返回完全相同：", saved_data["content"] == original)
    print("\n记住：长正文保存到 Backend，工具消息保留路径和预览；并没有把全文丢掉。")
    print("上面比较的是字符数，不是 token 数，更不是实际费用。")


if __name__ == "__main__":
    main()
