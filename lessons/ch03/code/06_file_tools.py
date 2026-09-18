"""实验 06：真正执行 Agent 的七种文件工具，但暂时不连接大模型。

运行：.venv/bin/python lessons/ch03/code/06_file_tools.py
区别：前面是 backend.read(...)；这里是工具请求 read_file → Backend.read。
工具名和参数由我们写好；文件工具、参数校验与返回消息都是真实的。
"""

from pathlib import Path
from uuid import uuid4

from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware, FilesystemState
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode


def main():
    folder = Path(__file__).resolve().parent / "output" / "06_tools"
    folder.mkdir(parents=True, exist_ok=True)
    backend = FilesystemBackend(root_dir=folder, virtual_mode=True)

    # Middleware 提供工具对象，其中工具函数会调用上面的 backend。
    middleware = FilesystemMiddleware(backend=backend)
    # ToolNode 是工具执行器：根据消息里的工具名找到函数，并传入参数。
    builder = StateGraph(FilesystemState)
    builder.add_node("tools", ToolNode(middleware.tools))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile()

    def use_tool(name, **arguments):
        # AIMessage 是模型消息的格式。这里只是手工填写请求，不是调用 AI。
        # 每次只执行一个工具，确保“先写再读”，不会并行抢跑。
        request = AIMessage(content="", tool_calls=[{
            "name": name,
            "args": arguments,
            "id": uuid4().hex,  # 每次调用的唯一编号，返回消息会与它对应。
        }])
        result = graph.invoke({"messages": [request]})
        response = result["messages"][-1]  # 最后一条是工具返回的 ToolMessage。
        print(f"\n调用 {name}，参数：{arguments}")
        print("状态：", response.status)
        print("结果：", response.content)
        return response

    # 七种工具按日常操作顺序执行，不需要先学通用测试框架。
    assert use_tool("write_file", file_path="/shopping.txt", content="苹果\n牛奶\n面包").status == "success"
    assert use_tool("ls", path="/").status == "success"
    assert use_tool("read_file", file_path="/shopping.txt", offset=1, limit=1).status == "success"
    assert use_tool("edit_file", file_path="/shopping.txt", old_string="牛奶", new_string="豆浆").status == "success"
    assert use_tool("glob", pattern="*.txt", path="/").status == "success"
    assert use_tool("grep", pattern="豆浆", path="/", output_mode="content").status == "success"

    # 只删除单独创建的练习文件，保留购物清单供你打开查看。
    assert use_tool("write_file", file_path="/remove_me.txt", content="临时文件").status == "success"
    assert use_tool("delete", file_path="/remove_me.txt").status == "success"
    missing = use_tool("read_file", file_path="/remove_me.txt")
    assert missing.status == "error"  # 预期失败：证明工具会反馈“找不到文件”。

    print("\n记住：工具是 Agent 的操作入口；Backend 是入口后面的存储实现。")
    print("本实验只挂载了文件工具，没有挂载完整 Agent 的卸载/摘要调用链。")
    print("下一步只需让真实模型生成工具请求，就是实验 07 的工作方式。")


if __name__ == "__main__":
    main()
