# 05｜自动卸载、摘要与上下文预算实验

本节依赖第 03 部分公共代码。目标是证明：完整内容可以保存在 Backend，模型历史只保留引用或摘要；然后讨论这样做仍然有哪些限制。

## 1. 不同机制处理不同问题

| 机制 | 触发对象 | 主要作用 | 不能保证的事情 |
|---|---|---|---|
| 手动写证据文件 | 应用或模型主动写入 | 提供稳定资料地址 | 不会自动筛选正确证据 |
| 分页读取 | 某个读取请求 | 限制单次取回量 | 不保证跨页快照一致 |
| 大工具结果卸载 | 超过阈值的工具输出文本 | 用引用替代大段输出 | 不自动缩小 State/数据库总体积 |
| 大用户消息卸载 | 很大的用户文本 | 减少模型请求的文本压力 | 不代表原消息从所有存储中删除 |
| 旧工具参数裁剪 | 历史工具参数 | 降低旧调用在上下文中的负担 | 不等于所有参数都完整转存 |
| 对话摘要 | 较长的历史 | 保留继续任务所需的信息 | 有损，可能遗漏约束和证据 |

不要把它们统一描述成“输入输出超过 20K 就自动完整保存”。`0.7.14` 的工具结果卸载阈值默认是 20,000，但这一条路径使用 `4 × 阈值` 的字符数近似；它不是调用模型 tokenizer 计算出来的精确 token 数。大用户消息另有默认 50,000 的阈值配置，旧工具参数又是不同机制。

对于中文、代码、表情和混合内容，字符数近似与真实 token 数可能偏差明显。阈值是策略参数，不是模型硬上限。

## 2. 自动卸载的真实数据流

```mermaid
sequenceDiagram
    participant M as 模型
    participant T as 业务工具
    participant W as FilesystemMiddleware
    participant B as Backend
    M->>T: 请求资料
    T-->>W: 很大的工具结果
    W->>W: 提取文本并检查阈值
    W->>B: 保存完整文本
    B-->>W: 写入结果
    W-->>M: 保存路径 + 内容预览
    M->>B: 经 grep/read_file 读取必要部分
    B-->>M: 局部证据
```

默认工具结果目录位于 `/large_tool_results/`；Composite 的 `artifacts_root` 可以改变前缀。文件名包含调用标识等实现细节，应用不应该猜一个固定文件名。工具回复中的真实引用是导航依据。

当前预览含头部和尾部片段，不应背成“永远只显示前 10 行”。多模态内容中，文本卸载与非文本内容保留也需要分开理解。

文件工具本身在通用卸载排除列表中，包括 `read_file`、`grep` 等；它们有各自的分页或输出限制。否则读取一份卸载文件，又把读取结果卸载成新文件，会产生循环引用。

## 3. 实验 H：大结果被保存、缩短并能够回读

我们将阈值降低为 1,000，用约 40 KB 的合成资料触发，不需要构造真实的几十万 token 响应。数据中间埋入一条可核对证据，用来说明仅看头尾预览无法覆盖全部信息。

```python
# runnable: offload
from langchain_core.tools import tool
from deepagents.middleware.filesystem import FilesystemMiddleware

payload_lines = [f"entry-{i:04d}: " + "abcdefghij" * 4 for i in range(700)]
payload_lines[350] = "EVIDENCE-MIDDLE: cache_ttl_seconds=37"
payload = "\n".join(payload_lines)


@tool
def large_evidence() -> str:
    """返回实验用的大型证据文本。"""
    return payload


backend = StateBackend()
agent = make_agent(
    backend,
    tools=[large_evidence],
    middleware=[FilesystemMiddleware(
        backend=backend,
        tool_token_limit_before_evict=1000,
    )],
)
result, output = run_steps(agent, [call("large_evidence")], verbose=False)
assert_statuses(output, ["success"])
saved = {
    path: data for path, data in result["files"].items()
    if path.startswith("/large_tool_results/")
}
assert len(saved) == 1
saved_path, saved_data = next(iter(saved.items()))
assert saved_data["content"] == payload
assert saved_path in output[0].content
assert len(output[0].content) < len(payload)
assert "EVIDENCE-MIDDLE" not in output[0].content
print("原文本字符数：", len(payload))
print("替代消息字符数：", len(output[0].content))
print("保存路径：", saved_path)

_, recovered = run_steps(agent, [
    call("grep", pattern="EVIDENCE-MIDDLE", path="/large_tool_results/", output_mode="content"),
    call("read_file", file_path=saved_path, offset=348, limit=5),
], verbose=False)
assert_statuses(recovered, ["success", "success"])
assert "cache_ttl_seconds=37" in recovered[0].content
assert "cache_ttl_seconds=37" in recovered[1].content
print("PASS: 卸载内容完整；中间证据可以搜索并分页回读")
```

### 3.1 为什么传同一个 Backend 给两个地方

`create_deep_agent` 自带 FilesystemMiddleware。`0.7.14` 按中间件名称替换同名默认实例，因此这里提供定制的 FilesystemMiddleware 来调整阈值。将它与 `backend=` 指向同一个对象，可避免工具读写和卸载被误配置到不同存储。

这一替换行为是版本相关的，本项目源码在 `_apply_custom_middleware` 中实现。不要把本配置不加核对地用于旧版。

### 3.2 这个实验究竟验证了什么

验证了真实业务工具结果被中间件截获，保存内容与原文一致，替代 ToolMessage 引用正确，后续文件工具能读回证据。

没有验证真实 LLM 是否会主动回读、真实 token 节省量、供应商费用和回答准确率。这里打印的是字符数，不能标成 token 数或直接换算为节省金额。

### 3.3 路径丢失会怎样

一旦卸载文件被清理、切换到另一个线程、或 Backend 故障，摘要/消息中的引用可能无法解析。因此必须设计引用生命周期：还可能被使用的证据，不应被后台清理任务提前删除。

## 4. 自动摘要：压缩的是信息表示，不是事实风险

摘要需要保留任务目标、用户约束、已完成操作、关键结论及依据、产物位置、未完成工作。只保留“我们研究了缓存”无法支持下一轮可靠继续。

本版本默认摘要策略依赖模型 profile：已知 `max_input_tokens` 时，常用触发阈值为窗口的 85%，近期保留窗口为 10%；profile 缺失时，源码使用固定 token/消息回退配置，包括 170,000 token 的摘要触发值。不能假定所有自定义模型都会自动按它真实的小窗口大小触发。

摘要、工具参数裁剪和结果卸载的具体执行顺序由中间件控制。原课程中简化的“两道防线”适合入门理解，不应当作所有版本的严格状态机规范。

## 5. 实验 I：验证摘要的归档与继续执行机制

本实验刻意使用固定摘要模型，测试中间件能否执行和归档，不测试摘要语言质量。主模型与摘要模型都不访问外部服务。

```python
# runnable: summarization
from deepagents.middleware.summarization import SummarizationMiddleware


class FixedReplyModel(BaseChatModel):
    reply: str = "已收到本轮消息。"

    @property
    def _llm_type(self):
        return "ch03-fixed-reply"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
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
        trigger=("messages", 6),
        keep=("messages", 2),
    )],
)
config = {"configurable": {"thread_id": "summary-lab"}}
for i in range(8):
    result = agent.invoke(
        {"messages": [HumanMessage(content=f"ORIGINAL-{i}: 本轮证据及约束。")]},
        config=config,
    )
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
```

这个实验不应通过 `len(result["messages"])` 单独推断“真实模型输入缩短了多少”。图中的保存状态、摘要事件和最终送给模型的请求视图可能不同；要测模型输入，需在模型调用处记录实际请求内容或 token usage。

### 5.1 真实摘要质量如何测

创建含明确约束的多轮对话，例如“不得使用外网”“报告必须引用两个文件”“第一版结论已被后续证据否定”。在摘要前后分别问同一组问题，比较约束保留率、事实正确率和产物可定位率。

摘要只能作为导航和工作记忆。对关键数值、权限、用户批准和不可逆操作，应该查权威状态或原始证据，不能仅凭摘要推断。

## 6. 膨胀会转移到哪里

把 5 MB 文本从 ToolMessage 搬到 StateBackend 的 `files`，可能减少模型请求中的正文，但这些内容仍需保存在图状态。若检查点频繁、文件重复改写，序列化、内存和存储压力会增长。实际是否去重以及如何增量保存取决于 Checkpointer。

长期大型原文通常更适合外部对象/文件存储；State 中保存任务所需引用和少量中间状态。检索索引可以单独维护，前提是索引与原文版本一致。

## 7. 一份可执行的上下文预算策略

对于研究任务，可以采用以下应用策略，而非仅依赖自动触发阈值：

1. 每份原始资料保存来源、抓取时间、内容哈希和可信等级。
2. 原文入库后生成短索引，索引只负责导航。
3. 每轮限制取回文件数、窗口行数与估算 token。
4. 搜索截断时先缩小范围，再查询，而不是盲目放大返回上限。
5. 关键结论必须关联来源路径和版本；总结时保留关联。
6. 任务结束后固化报告与证据版本，再清理无引用的临时产物。

## 8. 评估指标与反例

| 指标 | 定义示例 | 易产生的误判 |
|---|---|---|
| 引用可解析率 | 能成功打开的引用 / 全部引用 | 文件存在但内容已被覆盖 |
| 证据支持率 | 确实被证据支持的断言 / 抽样断言 | 引用了同主题文档就算支持 |
| 检索召回 | 找回的关键证据 / 已知关键证据 | 用所有返回行数替代关键证据数量 |
| 分页完整性 | 没有遗漏/重复的源行或记录比例 | 只验证第一页 |
| 模型输入规模 | 实际请求 token usage | 把字符数直接叫作 token |
| 存储放大 | 总保存字节 / 唯一原文大小 | 忽略检查点、备份和历史版本 |
| 任务完成率 | 达到验收条件的任务占比 | 模型说“完成”就计为通过 |

下一节：[生产设计与自定义扩展](06-production-and-customization.md)。
