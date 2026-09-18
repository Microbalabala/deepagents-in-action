"""实验 03：同一张便签，换个会话还能看到吗？

运行：.venv/bin/python lessons/ch03/code/03_state_vs_filesystem.py
只比较一个变量：Backend。两组都按“A 写 → A 读 → B 读”执行。
"""

from pathlib import Path

from deepagents.backends import FilesystemBackend, StateBackend
from deepagents.middleware.filesystem import FilesystemState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


# StateBackend 必须在图运行时中使用，不能像磁盘后端一样在顶层直接 write。
# FilesystemState 已经定义好 files 字段及其更新规则，我们直接复用。
# 新增两个字段：action 表示本次做什么；answer 保存给我们看的结果。
class LabState(FilesystemState):
    action: str
    answer: str
    readable: bool


def compare_one_backend(name, backend):
    # 这个函数就是图里唯一的工作步骤。暂时把“图”理解成一个运行容器。
    def file_step(state):
        if state["action"] == "write":
            result = backend.write("/note.txt", "会话 A 的便签：明天学习 Store。")
            assert result.error is None, result.error
            return {"answer": "写入成功", "readable": True}

        result = backend.read("/note.txt")
        if result.error:
            return {"answer": "读不到：这个会话没有该文件", "readable": False}
        return {"answer": "读到了：" + result.file_data["content"], "readable": True}

    # 固定流程只有一站：开始 → 文件操作 → 结束，没有大模型和复杂规划。
    builder = StateGraph(LabState)
    builder.add_node("file_step", file_step)
    builder.add_edge(START, "file_step")
    builder.add_edge("file_step", END)

    # Saver 像一个按“会话号”存放状态的柜子，本实验的柜子只存在于进程内存。
    # Backend 决定文件存在哪里；Saver 决定图状态怎样被保存，两者职责不同。
    graph = builder.compile(checkpointer=InMemorySaver())
    conversation_a = {"configurable": {"thread_id": "A"}}
    conversation_b = {"configurable": {"thread_id": "B"}}

    print(f"\n--- {name} ---")
    written = graph.invoke({"action": "write"}, config=conversation_a)
    print("1. A 写入：", written["answer"])
    same = graph.invoke({"action": "read"}, config=conversation_a)
    print("2. A 读取：", same["answer"])
    other = graph.invoke({"action": "read"}, config=conversation_b)
    print("3. B 读取：", other["answer"])
    assert same["readable"] is True
    return other["readable"]


def main():
    folder = Path(__file__).resolve().parent / "output" / "03_comparison"
    folder.mkdir(parents=True, exist_ok=True)

    state_shared = compare_one_backend("StateBackend：按会话保存", StateBackend())
    disk_shared = compare_one_backend(
        "FilesystemBackend：共享同一个磁盘目录",
        FilesystemBackend(root_dir=folder, virtual_mode=True),
    )
    assert state_shared is False
    assert disk_shared is True

    print("\n最终对照：                    A 读       B 读")
    print("StateBackend                 能         不能")
    print("FilesystemBackend（同目录）   能         能")
    print("\n记住：换 thread_id 会换 State；不会自动换磁盘目录。")
    print("补充：持久化 Saver 能恢复同线程的 State；InMemorySaver 不能抗进程重启。")
    print("练一练：把 conversation_b 的 thread_id 改为 A，再预测结果。断言也要随预期修改。")


if __name__ == "__main__":
    main()
