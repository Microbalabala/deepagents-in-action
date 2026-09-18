"""实验 07（可选）：让真实模型自己决定怎样读写文件。

运行：.venv/bin/python lessons/ch03/code/07_real_agent.py
需要项目现有的 OpenAI 兼容模型配置，会产生模型请求。
前 6 个实验不依赖这个实验；编写新版讲义时未请求真实模型。
"""

import os
from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI


def main():
    # 文件位置为 项目/lessons/ch03/code/07_real_agent.py，parents[3] 就是项目根。
    project = Path(__file__).resolve().parents[3]
    # 只由应用加载配置；后面 Agent 的文件根目录不包含这个 .env。
    load_dotenv(project / ".env", override=False)
    if os.getenv("AGENTSEEK_MODEL_PROVIDER", "openai") != "openai":
        raise SystemExit("本例使用 OpenAI 兼容接口；其他供应商请替换 ChatOpenAI 初始化部分。")
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("AGENTSEEK_MODEL"):
        raise SystemExit("请先配置 OPENAI_API_KEY 和 AGENTSEEK_MODEL；不要把密钥写进实验代码。")

    model = ChatOpenAI(
        model=os.environ["AGENTSEEK_MODEL"],
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_API_BASE") or None,
    )
    folder = Path(__file__).resolve().parent / "output" / "07_agent"
    folder.mkdir(parents=True, exist_ok=True)
    backend = FilesystemBackend(root_dir=folder, virtual_mode=True)

    # 预先放一份小材料。模型要通过 read_file 获取正文，不是从提问中直接得到它。
    source = "StateBackend：文件属于会话状态。\nFilesystemBackend：文件保存在磁盘。\nStoreBackend：同一 namespace 可以共享资料。"
    assert backend.write("/input/notes.txt", source).error is None
    # 删除本实验上一轮的输出，避免模型本轮没写文件却误用旧产物验收。
    output_path = folder / "summary.md"
    if output_path.exists():
        output_path.unlink()

    # create_deep_agent 已内置文件工具，我们只需提供模型和 Backend。
    agent = create_deep_agent(
        model=model,
        backend=backend,
        permissions=[FilesystemPermission(
            operations=["write"], paths=["/input/**"], mode="deny",
        )],
        system_prompt="直接使用文件工具完成任务，不委派子任务。必须先读取原文，再保存结果。",
    )
    print("正在请求模型：读取 notes.txt，并把三条学习笔记保存为 summary.md……")
    result = agent.invoke(
        {"messages": [{"role": "user", "content":
            "读取 /input/notes.txt。仅依据原文，用中文写出三个 Backend 各自的作用，"
            "保存到 /summary.md，最后用 read_file 回读确认。"}]},
        config={"recursion_limit": 30},
    )

    # 打印模型实际发起的请求，以及真实工具返回。不要只看模型的最后一句话。
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            for request in message.tool_calls:
                print("模型选择工具：", request["name"], request["args"])
        elif isinstance(message, ToolMessage):
            print("工具结果：", message.name, message.status)

    assert output_path.is_file(), "模型没有真正创建 summary.md，请检查上面的工具结果。"
    summary = output_path.read_text(encoding="utf-8")
    assert summary.strip(), "输出文件为空。"
    assert backend.read("/input/notes.txt").file_data["content"] == source
    print("\n真实输出文件：", output_path)
    print(summary)
    print("记住：真实模型只替代了实验 06 中手工填写工具请求的部分。")
    print("文件存在还不代表内容正确，请对照 notes.txt 检查三条解释。")


if __name__ == "__main__":
    main()
