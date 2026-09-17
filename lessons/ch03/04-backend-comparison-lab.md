# 04｜State、Filesystem、Store 与 Composite 对比实验

本节依赖 [第 03 部分的公共实验代码](03-file-tools-lab.md)。所有对比使用相同工具链；磁盘路径限定在临时目录。本节满足“至少两种 Backend 对比”的基本要求，并进一步测试三种存储后端和一种路由后端。

## 1. 先提出假设，再执行代码

公平的实验需要控制变量。保持模型驱动、输入内容、工具调用顺序和断言一致，只改变 Backend。不要把一个配置使用大模型，另一个使用小模型，再把答案质量差异归因于存储。

| 条件 | State + InMemorySaver | Filesystem，同 root | Store，同 Store/namespace |
|---|---|---|---|
| 同一轮写后读 | 能看到 | 能看到 | 能看到 |
| 同一线程下一次调用 | 能看到 | 能看到 | 能看到 |
| 换一个 thread_id | 看不到 | 能看到 | 能看到 |
| 新 Agent，复用原 Saver/存储 | 同 thread 能看到 | 同 root 能看到 | 同 Store/namespace 能看到 |
| 新 Agent，新 Saver，外部存储仍复用 | 看不到 | 能看到 | 能看到 |
| 换 namespace | 不适用 | 不适用 | 看不到 |
| 杀掉进程并恢复 | 本实验 Saver 丢失 | 文件根目录仍存在时可恢复 | 本实验 InMemoryStore 丢失 |

最后一行涉及真正的进程生命周期，下面的主矩阵通过对象重建测试作用域；另有独立双进程磁盘实验验证进程边界。不要将“重建对象”写成“进程重启”。

## 2. 实验 D：相同文件操作 + 跨线程矩阵

```python
# runnable: backend_matrix
def exercise_backend(label, backend_factory, *, store=None, disk_root=None):
    saver = InMemorySaver()
    agent = make_agent(backend_factory(), store=store, checkpointer=saver)

    result, output = run_steps(agent, [
        call("write_file", file_path="/work/probe.txt", content="version=1\nowner=ch03\n"),
        call("edit_file", file_path="/work/probe.txt", old_string="version=1", new_string="version=2"),
        call("read_file", file_path="/work/probe.txt", offset=0, limit=10),
    ], thread="A", verbose=False)
    assert_statuses(output, ["success"] * 3)
    assert "version=2" in output[-1].content

    _, same = run_steps(agent, [call("read_file", file_path="/work/probe.txt")], thread="A", verbose=False)
    _, other = run_steps(agent, [call("read_file", file_path="/work/probe.txt")], thread="B", verbose=False)

    rebuilt_shared = make_agent(backend_factory(), store=store, checkpointer=saver)
    _, shared = run_steps(rebuilt_shared, [call("read_file", file_path="/work/probe.txt")], thread="A", verbose=False)

    rebuilt_fresh = make_agent(backend_factory(), store=store)
    _, fresh = run_steps(rebuilt_fresh, [call("read_file", file_path="/work/probe.txt")], thread="A", verbose=False)

    expected_other = "error" if label == "State" else "success"
    assert same[0].status == "success"
    assert shared[0].status == "success"
    assert other[0].status == expected_other
    assert fresh[0].status == expected_other

    # 独立读取真实保存位置，防止只相信模型/工具展示。
    if label == "State":
        assert result["files"]["/work/probe.txt"]["content"] == "version=2\nowner=ch03\n"
    elif label == "Filesystem":
        assert (Path(disk_root) / "work/probe.txt").read_text() == "version=2\nowner=ch03\n"
    else:
        stored = backend_factory().read("/work/probe.txt")
        assert stored.error is None
        assert stored.file_data["content"] == "version=2\nowner=ch03\n"

    return [label, same[0].status, other[0].status, shared[0].status, fresh[0].status]


with TemporaryDirectory(prefix="ch03-matrix-") as directory:
    memory_store = InMemoryStore()
    rows = [
        exercise_backend("State", StateBackend),
        exercise_backend(
            "Filesystem",
            lambda: FilesystemBackend(root_dir=directory, virtual_mode=True),
            disk_root=directory,
        ),
        exercise_backend(
            "Store",
            lambda: StoreBackend(store=memory_store, namespace=lambda _rt: ("ch03", "alice")),
            store=memory_store,
        ),
    ]
    print("Backend | 同线程 | 不同线程 | 新Agent共享Saver | 新Agent新Saver")
    for row in rows:
        print(" | ".join(row))
print("PASS: 三种 Backend 生命周期矩阵及底层内容验证")
```

预期结果：

```text
State | success | error | success | error
Filesystem | success | success | success | success
Store | success | success | success | success
```

### 2.1 结果意味着什么

State 的隔离来自图状态作用域。新建 Backend 实例不会得到一份独立持久化文件库；是否看到文件取决于图运行绑定到哪个线程状态。

Filesystem 的文件存在磁盘上，更换线程或 Saver 不会改变磁盘内容。两个用户共用一个 root，也会共享文件，除非另有可靠授权机制。

Store 的共享来自同一个 Store 与 namespace。Checkpointer 是否相同不会改变独立 Store 中的条目。

### 2.2 结果不意味着什么

它没有证明某后端速度更快，也没有证明线程安全或事务安全。顺序写后读测试只验证当前顺序执行场景。

`success` 只说明本次请求成功。生产可靠性还要测试进程退出、断网、存储拒绝、并发写入和恢复流程。

## 3. 实验 E：用户 namespace 与线程隔离必须同时考虑

本实验用 dataclass 注入运行上下文。这里的用户身份来自测试代码；生产中应由服务端认证结果生成，而不是让模型从用户输入中选择 namespace。

```python
# runnable: namespace
@dataclass(frozen=True)
class SessionContext:
    tenant_id: str
    user_id: str


store = InMemoryStore()
backend = StoreBackend(
    namespace=lambda rt: (rt.context.tenant_id, rt.context.user_id, "files"),
)
agent = make_agent(backend, store=store, context_schema=SessionContext)
alice = SessionContext("tenant-A", "alice")
bob = SessionContext("tenant-A", "bob")
other_tenant_alice = SessionContext("tenant-B", "alice")

_, wrote = run_steps(agent, [
    call("write_file", file_path="/profile.txt", content="language=zh-CN"),
], thread="alice-1", context=alice, verbose=False)
_, alice_read = run_steps(agent, [call("read_file", file_path="/profile.txt")],
    thread="alice-2", context=alice, verbose=False)
_, bob_read = run_steps(agent, [call("read_file", file_path="/profile.txt")],
    thread="bob-1", context=bob, verbose=False)
_, tenant_read = run_steps(agent, [call("read_file", file_path="/profile.txt")],
    thread="tenant-B-alice-1", context=other_tenant_alice, verbose=False)

assert wrote[0].status == "success"
assert alice_read[0].status == "success"
assert bob_read[0].status == "error"
assert tenant_read[0].status == "error"

items = store.search(("tenant-A", "alice", "files"))
assert len(items) == 1
print("实际 Store 键：", items[0].key)
print("PASS: 同用户跨线程共享；不同用户和不同租户隔离")
```

这里为不同用户同时使用了不同线程。原因是 **Store namespace 隔离不保护错误复用的检查点消息历史**。如果 Bob 被允许访问 Alice 的 thread_id，即使 Store 不泄露，历史 ToolMessage 也可能已经包含 Alice 的内容。

服务端必须验证“当前身份是否有权访问这个 thread_id”，并在数据库层或独立访问服务层实施授权。namespace 是数据组织方式，不是身份验证本身。

## 4. 实验 F：CompositeBackend 分离任务草稿与长期资料

```python
# runnable: composite
memory_store = InMemoryStore()
long_term = StoreBackend(store=memory_store, namespace=lambda _rt: ("ch03", "shared"))
backend = CompositeBackend(default=StateBackend(), routes={"/memories/": long_term})
agent = make_agent(backend, store=memory_store)

result, output = run_steps(agent, [
    call("write_file", file_path="/scratch/plan.md", content="EVIDENCE: 当前任务草稿"),
    call("write_file", file_path="/memories/preferences.md", content="EVIDENCE: 使用中文解释"),
    call("glob", pattern="**/*.md", path="/"),
    call("grep", pattern="EVIDENCE", path="/", output_mode="files_with_matches"),
], thread="work-1")
assert_statuses(output, ["success"] * 4)
assert "/scratch/plan.md" in result["files"]
assert "/memories/preferences.md" not in result.get("files", {})
assert "/memories/preferences.md" in output[2].content
assert "/scratch/plan.md" in output[3].content
assert "/memories/preferences.md" in output[3].content

# 直接查询目标 Backend：路由前缀已被移除。
assert long_term.read("/preferences.md").error is None
assert long_term.read("/memories/preferences.md").error is not None

_, next_thread = run_steps(agent, [
    call("read_file", file_path="/scratch/plan.md"),
    call("read_file", file_path="/memories/preferences.md"),
], thread="work-2")
assert_statuses(next_thread, ["error", "success"])
print("PASS: Composite 分流、搜索聚合和路由去前缀")
```

模型面对一个统一目录树，但不同目录有不同生命周期。应用应在工具说明或任务协议中讲清用途，避免把未经核实的任务草稿自动写进长期事实区。

### 4.1 验证最长前缀优先

```python
# runnable: longest_prefix
store = InMemoryStore()
general = StoreBackend(store=store, namespace=lambda _rt: ("general",))
team = StoreBackend(store=store, namespace=lambda _rt: ("team",))
router = CompositeBackend(
    default=StateBackend(),
    routes={"/memories/": general, "/memories/team/": team},
)
agent = make_agent(router, store=store)
_, output = run_steps(agent, [
    call("write_file", file_path="/memories/team/rules.md", content="team-rule"),
], verbose=False)
assert_statuses(output, ["success"])
assert team.read("/rules.md").error is None
assert general.read("/team/rules.md").error is not None
print("PASS: 最长路径前缀优先")
```

如果一个目录已经被路由“挂载”，默认后端中恰好存在相同前缀的数据，可能被路由遮蔽。应在迁移路由时检查历史文件，不能把新增路由视为零影响配置变化。

## 5. 实验 G：真正的双进程磁盘验证

依赖公共代码中的导入，但不依赖模型。本实验用当前 Python 解释器启动两个独立进程，临时根目录由父进程保留，第二个进程重新创建 Backend 后读取文件。

```python
# runnable: process_persistence
import subprocess
import sys

writer = '''
import sys
from deepagents.backends import FilesystemBackend
b = FilesystemBackend(root_dir=sys.argv[1], virtual_mode=True)
assert b.write("/probe.txt", "persisted-across-processes").error is None
'''
reader = '''
import sys
from deepagents.backends import FilesystemBackend
b = FilesystemBackend(root_dir=sys.argv[1], virtual_mode=True)
r = b.read("/probe.txt")
assert r.error is None
assert r.file_data["content"] == "persisted-across-processes"
print("PASS: 第二个进程读取到了第一个进程保存的文件")
'''
with TemporaryDirectory(prefix="ch03-process-") as directory:
    subprocess.run([sys.executable, "-c", writer, directory], check=True)
    subprocess.run([sys.executable, "-c", reader, directory], check=True)
```

这个结果依赖根目录在两个子进程之间仍存在。容器的可写层、临时 Pod 磁盘或清理策略会改变这一前提。

对 State 的真正恢复实验，需要持久化 Checkpointer；对 Store 的恢复实验，需要持久化 Store。仅把变量从 `memory_store` 改名为 `persistent_store` 没有任何效果。第 06 部分给出部署设计，数据库连接和迁移属于外部环境扩展实验。

## 6. 如何补做性能实验

上面的实验测语义，下面是性能实验设计，不伪造跨机器通用的性能结论。

1. 为每个 Backend 准备相同数量、相同大小和内容分布的文件。
2. 分别测写入、读取固定窗口、精确路径查询、小范围 grep、大范围 grep。
3. 将 Agent/模型耗时与 Backend 耗时分开；离线驱动只能消除模型 API 延迟，不能消除图编排开销。
4. 记录预热、样本数、p50/p95/p99、峰值内存、存储字节和检查点大小。
5. State 必须在图内测；不能一边直接测 Filesystem，一边把 State 的全部 Agent 开销算入后端延迟。
6. 对磁盘说明是否缓存命中；对远程 Store 说明网络、连接池和查询分页。

可选择 `100/1000/10000` 个文件和 `1 KB/10 KB/100 KB` 三档。先运行小档确认语义，再逐步扩大。不要直接将数千个大文件塞进 State，然后把内存耗尽归因于“LLM 上下文太小”。

## 7. 实验报告应如何写

推荐按“假设 → 控制变量 → 实测 → 解释 → 限制 → 选型”组织。

例如：“相同 root 的 FilesystemBackend 在两个不同线程中读取相同文件都成功；说明 thread_id 不控制磁盘文件可见性。因此多用户任务需要独立目录或强制授权。该实验没有验证 OS 级隔离和并发一致性。”

这比“Filesystem 比 State 好，因为持久化”更准确。Backend 的优劣要与需求对应：任务临时空间、跨用户共享、跨进程恢复和代码执行是不同维度。

下一节：[上下文管理实验](05-context-engineering-lab.md)。
