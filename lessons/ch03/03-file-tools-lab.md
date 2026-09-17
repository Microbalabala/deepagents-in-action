# 03｜环境准备与七种文件工具实验

本节使用一个固定返回工具调用的测试模型。它不请求外部服务，不需要 API Key；**文件工具、中间件、Backend 和 LangGraph 执行链是真实的**。这样可以先测系统行为，避免把模型是否愿意调用某个工具混进存储实验。

这个测试模型不具备推理能力，不用于评估 LLM。真实模型的研究任务在第 07 部分单独完成。

## 1. 检查环境，先不要升级依赖

在项目根目录运行以下只读检查，或者在使用项目 `.venv` 的 Notebook 中运行等价 Python 代码。

```bash
.venv/bin/python - <<'PY'
import sys
from importlib.metadata import version
print(sys.version)
for name in ("deepagents", "langchain", "langchain-core", "langgraph", "langgraph-checkpoint"):
    print(name, version(name))
PY
```

编写本讲义时的环境：

```text
Python 3.12
deepagents 0.7.14
langchain 1.4.0
langchain-core 1.6.3
langgraph 1.2.11
langgraph-checkpoint 4.2.0
```

若需要在项目外搭建独立练习环境，可在自己选定的临时目录使用下面的命令。本次编写没有执行安装，也没有修改项目依赖。

```bash
python3.12 -m venv /tmp/ch03-learning-venv
/tmp/ch03-learning-venv/bin/python -m pip install \
  'deepagents==0.7.14' 'langchain==1.4.0' \
  'langchain-core==1.6.3' 'langgraph==1.2.11' \
  'langgraph-checkpoint==4.2.0'
```

这固定了主要包，但不等于锁定全部传递依赖。严格复现应同时保留完整锁文件、Python 版本和操作系统信息。本项目已有 `uv.lock`，不要为学习本章随意运行全项目升级。

## 2. 公共实验代码：后续离线实验只需加载一次

下面是完整可运行代码。复制到 Notebook 的第一个代码单元；后续标注“依赖公共实验代码”的代码块在同一内核运行。

```python
# runnable: common
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import (
    StateBackend, FilesystemBackend, StoreBackend, CompositeBackend,
)


class ScriptedToolModel(BaseChatModel):
    """只执行给定工具序列，不连接模型供应商。"""

    @property
    def _llm_type(self):
        return "ch03-scripted-tool-model"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        # 固定脚本已包含工具名；真正的 Schema 校验由工具执行层处理。
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # 找到最新一轮实验请求，只统计该请求后已完成的工具调用。
        start = max(
            i for i, message in enumerate(messages)
            if isinstance(message, HumanMessage)
        )
        steps = json.loads(messages[start].content)["steps"]
        completed = sum(
            isinstance(message, ToolMessage)
            for message in messages[start + 1:]
        )
        if completed >= len(steps):
            response = AIMessage(content="实验调用序列执行完毕。")
        else:
            step = steps[completed]
            response = AIMessage(
                content="",
                tool_calls=[{
                    "name": step["name"],
                    "args": step["args"],
                    "id": uuid.uuid4().hex,
                    "type": "tool_call",
                }],
            )
        return ChatResult(generations=[ChatGeneration(message=response)])


def call(name, **args):
    return {"name": name, "args": args}


def make_agent(backend, *, store=None, checkpointer=None, **kwargs):
    return create_deep_agent(
        model=ScriptedToolModel(),
        backend=backend,
        store=store,
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        **kwargs,
    )


def run_steps(agent, steps, *, thread="lab-A", context=None, verbose=True):
    result = agent.invoke(
        {"messages": [HumanMessage(content=json.dumps({"steps": steps}))]},
        config={
            "configurable": {"thread_id": thread},
            "recursion_limit": 100,
        },
        context=context,
    )
    messages = result["messages"]
    start = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    outputs = [m for m in messages[start + 1:] if isinstance(m, ToolMessage)]
    assert len(outputs) == len(steps), "工具数量异常，请查看消息轨迹"
    if verbose:
        for index, output in enumerate(outputs, start=1):
            print(f"[{index}] {output.name}: {output.status}")
            print(str(output.content)[:900])
    return result, outputs


def assert_statuses(outputs, expected):
    actual = [output.status for output in outputs]
    assert actual == expected, (actual, expected)


print("公共实验代码已加载；没有调用外部模型。")
```

### 2.1 为什么每次只发一个工具调用

写文件后立刻读取依赖执行顺序。把二者放进同一个模型消息的并行工具列表，可能读到写入前的数据。这里每轮发一个调用，工具返回之后才发下一个，用确定的顺序测试存储语义。

### 2.2 为什么保留 `ToolMessage.status`

自然语言回复中可能包含“Error”，但不应靠字符串猜测失败。工具消息提供状态。对结构化 Backend 结果，则检查 `error` 字段。实验同时检查结果内容和最终保存的数据。

### 2.3 公共驱动的适用边界

它假定每个步骤产生一条工具结果，不处理真实模型推理、多模态消息、人工审批中断或摘要替换后的脚本恢复。它是本章短程确定性实验的驱动，不是生产 Agent 实现。

## 3. 实验 A：七种工具与关键失败分支

依赖上面的公共实验代码。本实验从一个新 Agent 和新线程开始，重复执行不会复用之前的文件。

```python
# runnable: file_tools
agent = make_agent(StateBackend())
text = "alpha\nbeta\nTODO x\nTODO y\n"
steps = [
    call("write_file", file_path="/work/a.txt", content=text),
    call("ls", path="/work/"),
    call("read_file", file_path="/work/a.txt", offset=1, limit=2),
    call("glob", pattern="**/*.txt", path="/work/"),
    call("grep", pattern="TODO", path="/work/", output_mode="files_with_matches"),
    call("grep", pattern="TODO", path="/work/", output_mode="content"),
    call("grep", pattern="TODO", path="/work/", output_mode="count"),
    # 两处 TODO，默认不能猜测改哪一处，应返回错误。
    call("edit_file", file_path="/work/a.txt", old_string="TODO", new_string="DONE"),
    call("edit_file", file_path="/work/a.txt", old_string="TODO", new_string="DONE", replace_all=True),
    call("read_file", file_path="/work/a.txt", offset=0, limit=20),
    # 当前版本会完整覆盖：用于证明它不是追加。
    call("write_file", file_path="/work/a.txt", content="only new\n"),
    call("read_file", file_path="/work/a.txt", offset=0, limit=20),
    call("write_file", file_path="/scratch/remove.txt", content="temporary"),
    call("delete", file_path="/scratch/"),
    call("read_file", file_path="/scratch/remove.txt", offset=0, limit=20),
]
result, outputs = run_steps(agent, steps)
expected = ["success"] * len(steps)
expected[7] = "error"
expected[14] = "error"
assert_statuses(outputs, expected)
assert "beta" in outputs[2].content and "TODO x" in outputs[2].content
assert "next offset 3" in outputs[2].content
assert "/work/a.txt" in outputs[3].content
assert "/work/a.txt: 2" in outputs[6].content
assert "DONE x" in outputs[9].content and "DONE y" in outputs[9].content
assert "only new" in outputs[11].content and "alpha" not in outputs[11].content
assert result["files"]["/work/a.txt"]["content"] == "only new\n"
assert "/scratch/remove.txt" not in result["files"]
print("PASS: 七种工具、歧义失败、覆盖写和目录删除")
```

最后两次失败是**预期测试通过**：歧义替换应该失败，删除后的文件应该不存在。测试不是要求所有操作都成功，而是要求系统按契约成功或拒绝。

其中对 `next offset 3`、计数文本的断言是当前版本的展示回归检查，升级后要重新审查。生产逻辑不应依赖这些字符串作为唯一协议。

## 4. 实验 B：证明 `grep` 不是正则

```python
# runnable: literal_grep
agent = make_agent(StateBackend())
_, outputs = run_steps(agent, [
    call("write_file", file_path="/search/example.txt", content="a.b\naxb\na.b a.b\n"),
    call("grep", pattern="a.b", path="/search/", output_mode="content"),
    call("grep", pattern="a.b", path="/search/", output_mode="count"),
    call("grep", pattern="a.*b", path="/search/", output_mode="content"),
])
assert_statuses(outputs, ["success"] * 4)
assert "a.b" in outputs[1].content and "axb" not in outputs[1].content
assert "/search/example.txt: 2" in outputs[2].content
assert "No matches found" in outputs[3].content
print("PASS: 字面量匹配；count 统计匹配行而非所有出现次数")
```

解释：第一行和第三行各贡献一条匹配，第三行出现两次 `a.b` 也不会把匹配行数变成 3。要统计业务实体或关键词出现总次数，应使用专门逻辑，而不是误用 `grep count`。

## 5. 实验 C：结构化分页与搜索截断

这一块使用 FilesystemBackend 的公开方法，展示 Backend 层的结果。它与前面经工具层调用的实验相互补充，不会将 StateBackend 从图环境中直接拿出来调用。

```python
# runnable: pagination
with TemporaryDirectory(prefix="ch03-page-") as directory:
    backend = FilesystemBackend(root_dir=directory, virtual_mode=True)
    original = "\n".join(f"row-{i:02d} TODO" for i in range(12))
    assert backend.write("/large.txt", original).error is None

    offset = 0
    lines = []
    while True:
        page = backend.read("/large.txt", offset=offset, limit=5)
        assert page.error is None and page.file_data is not None
        print(page.start_line, page.end_line, page.next_offset)
        lines.extend(page.file_data["content"].splitlines())
        if page.next_offset is None:
            break
        assert page.next_offset > offset, "分页必须前进，避免死循环"
        offset = page.next_offset
    assert lines == original.splitlines()

    limited = backend.grep("TODO", path="/", max_count=3)
    assert limited.error is None
    assert len(limited.matches) == 3
    assert limited.truncated is True
    print("截断：", limited.truncated, "已返回：", len(limited.matches))
print("PASS: 分页覆盖全部源行；有限搜索明确标注截断")
```

预期分页窗口为 `1–5`、`6–10`、`11–12`。实际只返回三个匹配时，`truncated=True` 告诉你仍有未返回的部分。

对正在被修改的文件逐页读取可能出现重复或遗漏。上面的实验文件在读取期间不变；生产需求若要求快照一致，应绑定文件版本、ETag 或内容哈希。

## 6. 观察记录模板

运行后不要只记录一句“成功”，至少填写下表。

| 项目 | 实际观察 | 解释 |
|---|---|---|
| `read_file(offset=1, limit=2)` | 记录正文和下一偏移量 | 0 基偏移与 1 基行范围的对应 |
| 重复旧字符串的编辑 | 记录 error 状态 | 精确编辑不会擅自选择一处 |
| 同路径再次 write | 记录最终文件内容 | 覆盖，非追加 |
| `grep("a.b")` | 记录命中的行 | 字面量语义 |
| `count` | 记录数字 | 匹配记录数，不是词频 |
| 删除目录后读取 | 记录 error 状态 | 递归删除生效 |
| `max_count=3` | 记录 truncated | 成功不代表全集 |

## 7. 常见问题定位

| 现象 | 优先检查 |
|---|---|
| `StateBackend must be used inside...` | 是否在普通 Python 顶层直接调用 StateBackend |
| namespace 相关异常 | StoreBackend 是否显式提供 namespace；Runtime 是否存在 |
| `bind_tools` 未实现 | 是否完整复制了测试模型，而非直接实例化 BaseChatModel |
| 第二轮状态丢失 | Checkpointer 是否是同一对象、thread_id 是否相同 |
| 缺少 `files` 或文件不在 `files` | 是否使用外部 Backend；磁盘/Store 文件不必出现在图状态 |
| 页面内容与本文不同 | 核对实际版本和工具展示协议，不要直接改预期掩盖差异 |
| 递归上限异常 | 模型是否持续发工具；脚本是否按最新一轮统计完成数量 |

下一节：[Backend 对比实验](04-backend-comparison-lab.md)。
