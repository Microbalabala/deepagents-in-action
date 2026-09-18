"""实验 09（选学）：同样是写文件，为什么有的允许、有的拒绝？

运行：.venv/bin/python lessons/ch03/code/09_permissions.py
无需 API Key；固定请求用于确保每次都尝试一次禁止操作和一次允许操作。
"""

from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage


class FixedToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def main():
    folder = Path(__file__).resolve().parent / "output" / "09_permissions"
    folder.mkdir(parents=True, exist_ok=True)
    backend = FilesystemBackend(root_dir=folder, virtual_mode=True)
    # 应用先准备好规则文件；接下来限制的是 Agent 文件工具的写入。
    assert backend.write("/rules.txt", "原始规则：不许修改。").error is None
    draft = folder / "draft.txt"
    if draft.exists():
        draft.unlink()  # 只清理本实验上一轮的产物，避免把旧文件当作本轮成功。

    model = FixedToolModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "write_file", "id": "denied-write",
            "args": {"file_path": "/rules.txt", "content": "尝试篡改规则"},
        }]),
        AIMessage(content="", tool_calls=[{
            "name": "write_file", "id": "allowed-write",
            "args": {"file_path": "/draft.txt", "content": "可以修改的草稿"},
        }]),
        AIMessage(content="两次写入尝试完成。"),
    ])
    agent = create_deep_agent(
        model=model,
        backend=backend,
        permissions=[FilesystemPermission(
            operations=["write"],  # 此权限类别也用于文件编辑和删除。
            paths=["/rules.txt"],
            mode="deny",          # 拒绝，不会执行这次文件写入。
        )],
    )
    result = agent.invoke({"messages": [{"role": "user", "content": "执行两次写入实验。"}]})
    replies = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    for reply in replies:
        print(reply.status, reply.content)
    assert [reply.status for reply in replies] == ["error", "success"]

    # 再到真实存储检查，证明拒绝不是仅仅在文字上说“不可以”。
    assert backend.read("/rules.txt").file_data["content"] == "原始规则：不许修改。"
    assert draft.read_text(encoding="utf-8") == "可以修改的草稿"
    print("\n记住：Backend 决定存在哪里；Permission 决定这次文件工具操作能否执行。")
    print("没有匹配规则时默认允许，所以 draft.txt 可以写入。")
    print("权限只覆盖相应工具入口，不会自动限制任意 Python 或宿主机 Shell。")


if __name__ == "__main__":
    main()
