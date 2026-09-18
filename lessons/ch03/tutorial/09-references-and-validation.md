# 09｜来源索引、版本差异与验证记录

实验修订与验证日期：2026-09-18；最初源码核对日期：2026-09-17。讲义采用“本项目锁定环境 → 安装源码 → 实际执行结果”的证据顺序。网络资料用于主题覆盖和背景核对，不能覆盖本地版本的相反证据。

## 1. 在线来源

| 来源 | 在课程中的用途 | 阅读提醒 |
|---|---|---|
| [Datawhale 第 3 章](https://datawhalechina.github.io/deepagents-in-action/chapters/ch03-virtual-filesystem/) | 确定原始学习主题和基础实验范围 | 滚动更新，部分描述是入门简化 |
| [LangChain 官方 Backends](https://docs.langchain.com/oss/python/deepagents/backends) | 核对后端抽象、路径路由与扩展方向 | 页面中的 Quickstart 与正文也可能存在版本差异 |
| [LangGraph 官方 Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpointer 与 Store 的职责区别 | 具体部署和 API 初始化要继续核对当前集成 |
| [Deep Agents 官方变更记录](https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/CHANGELOG.md) | 升级时检查迁移说明 | main 分支会变化，不能替代固定版本源码 |

本讲义没有复刻原文章节正文；实验脚本、教学数据、验证断言、系统设计问题和讲解组织均为面向当前项目重新编写。

## 2. 本地实现是精确 API 的主要依据

安装包根目录：

```text
/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/
```

以下是本次读取过的实现入口；行号只对应当前安装版本，升级后可能变化。

| 内容 | 本地源码入口 | 对应讲义 |
|---|---|---|
| Agent 构造与同名中间件替换 | [graph.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/graph.py:204) | 01、05 |
| FileData、ReadResult、WriteResult 等结构 | [backends/protocol.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/protocol.py:187) | 02、03、06 |
| Backend 核心方法与异步默认适配 | [BackendProtocol](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/protocol.py:404) | 02、06 |
| State 在图上下文中读写通道 | [backends/state.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/state.py:38) | 01、02、04 |
| 磁盘根目录与 virtual_mode | [backends/filesystem.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/filesystem.py:91) | 02、04、06 |
| Store 显式实例与 namespace 求值 | [backends/store.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/store.py:90) | 02、04 |
| 最长路由、去前缀和结果聚合 | [backends/composite.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/backends/composite.py:195) | 02、04 |
| 文件权限类型与规则 | [FilesystemPermission](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/filesystem.py:386) | 02、06 |
| 工具定义、默认分页和中间件 | [middleware/filesystem.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/filesystem.py:972) | 02、03、05 |
| 大工具结果阈值与处理 | [工具输出卸载](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/filesystem.py:3280) | 05 |
| 摘要默认触发策略 | [compute_summarization_defaults](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/summarization.py:262) | 05、08 |
| 摘要中间件与归档 | [middleware/summarization.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/summarization.py:523) | 05 |
| 子 Agent 状态传入与结果回传 | [middleware/subagents.py](/Users/huanglei/Documents/code/research_deepagent/.venv/lib/python3.12/site-packages/deepagents/middleware/subagents.py:687) | 06、08 |

这些链接指向只读核对过的现有源码，没有修改安装包。系统设计中的 CAS、幂等、分层授权等内容属于基于实验语义的工程推导，文中没有将它们写成 Deep Agents 已自动实现的保证。

### 2.1 本次源码指纹

下表记录文件 SHA-256 的前 16 个十六进制字符，仅用于快速比对环境，不作为完整性或安全验证机制。

| 文件 | 指纹前缀 |
|---|---|
| `graph.py` | `2c0c9a5fc4a836b1` |
| `backends/protocol.py` | `ed4e9c8a9a9560cb` |
| `backends/state.py` | `5e91945e8462df67` |
| `backends/filesystem.py` | `eed9c6dc6dd1a4d4` |
| `backends/store.py` | `1f8fa6cb45e15570` |
| `backends/composite.py` | `7056af6b7afffe67` |
| `middleware/filesystem.py` | `08ec6d6970e4acb6` |
| `middleware/summarization.py` | `54d93bd17a417180` |

## 3. 原文与本地版本需要区分的地方

| 容易沿用的说法 | 本课程更精确的表述 | 证据 |
|---|---|---|
| State 对话结束就必然消失 | 可见范围是线程；保存/恢复取决于 Checkpointer 与状态管理 | State 源码、生命周期实验 |
| 只设置 thread_id 就能延续 | 需要同一保存系统或显式状态传递 | 生命周期实验 |
| Filesystem 的 virtual_mode 默认 False/必须显式传 | 本地 0.7.14 默认 True；课程仍显式设置 | 构造签名 |
| 读取正文始终逐行编号 | 本地结果可以为分页头加正文 | 文件工具实验 |
| FileData 是按行列表 | 本地 content 是字符串，另有 encoding | 协议源码与状态输出 |
| 自定义 WriteResult 返回 files_update | 本地结构没有该字段，State 自己发送通道更新 | 协议与 State 源码 |
| 20K 是精确 token 阈值 | 对应工具输出路径用字符数近似 | 文件中间件源码 |
| 所有大输入输出都按同一方式卸载 | 工具结果、用户消息、旧参数策略不同 | 文件与摘要中间件源码 |
| 卸载只预览前 10 行 | 本地采用头尾内容预览 | 卸载实验和实现 |
| 所有模型都在 85% 自动摘要 | 与 profile 是否提供窗口信息有关 | 摘要默认策略源码 |
| StoreBackend 代表抗重启数据库 | 取决于实际 Store，InMemoryStore 不抗重启 | Store 设计与运行配置 |
| 工具权限可以限制任意 Shell | 不覆盖任意执行，相关组合还存在支持限制 | 文件中间件实现 |

表中的更正不是否定原课程的教学价值，而是提醒：学习框架时，需要把概念解释与某个版本的代码契约分开。

## 4. 新版独立脚本验证记录

新版所有实验以 `.py` 文件交付。使用本项目已有 `.venv/bin/python` 直接运行，不提取 Markdown 代码、不共享内核、不要求先运行公共驱动。业务源码、依赖与锁文件没有修改。

| 文件 | 实际验证内容 | 结果 |
|---|---|---|
| 01_filesystem.py | 磁盘写读、真实路径、同根目录新 Backend 读取 | 通过 |
| 02_file_operations.py | 七类文件操作、分页、覆盖、删除后的错误 | 通过 |
| 03_state_vs_filesystem.py | 同一 A 写/A 读/B 读流程对比两个 Backend | 通过 |
| 04_store.py | 同 Store 同 namespace 共享、换 namespace/Store 不可见 | 通过 |
| 05_composite.py | 磁盘和 Store 路由、内部路径去前缀 | 通过 |
| 06_file_tools.py | ToolNode 真正执行七种 Agent 文件工具 | 通过 |
| 07_real_agent.py | 真实模型读写文件 | 静态语法检查，未请求模型 |
| 08_large_result.py | 真实中间件卸载，保存全文与原文一致 | 通过 |
| 09_permissions.py | 禁止规则文件写入，允许草稿写入；校验实际文件 | 通过 |
| advanced/10_audit_backend.py | 同步/异步操作记录和错误审计 | 通过 |
| advanced/11_optimistic_concurrency.py | 版本条件拒绝过期写入 | 通过 |
| advanced/12_summarization.py | 固定摘要模型触发归档，早期原文仍存在 | 通过 |
| advanced/13_research_report.py | 真实模型研究报告与证据校验 | 静态语法检查，未请求模型 |

共 **13 个独立脚本，其中 11 个离线脚本实际运行通过，2 个真实模型脚本只做静态检查**。固定模型只在部分选学实验负责发出请求，不模拟文件工具和存储结果。

### 4.1 关键实测输出

```text
                             A 读取     B 读取
StateBackend                 能         不能
FilesystemBackend（同目录）   能         能
```

```text
购物清单 offset=1, limit=1：牛奶；下一偏移量为 2
Store 同容器同 namespace：能读到
Store 同容器不同 namespace：读不到
Store 新容器同 namespace：读不到
长工具结果：47,389 字符 → 1,629 字符的替代工具消息
完整原文仍保存在 Backend，与原始返回完全相同
```

上面是当前受控实验的字符数，不代表真实模型通用的压缩率或费用节省。语义上“读不到”的具体原因，应结合 Backend 的 error 字段检查。

### 4.2 与原版实验的变化

原版以公共测试模型、消息统计和统一驱动起步，新版先直接观察 Backend，再通过只有一个 ToolNode 的图认识工具。进阶审计、并发和摘要保留为独立选学脚本；不再作为理解文件系统的前置要求。

磁盘入门产物保留在 `code/output/`，而不是立即删除的临时目录。State/Store 的内存数据不凭空变成磁盘文件，讲义明确指出这种差别。

## 5. 测试边界

- 真实模型：07 和进阶 13 未请求模型服务，没有读取项目凭证来执行收费实验。
- Store：04 测试存储对象与 namespace 作用域，不将对象重建说成进程重启或真实线程切换。
- 权限：09 实测两次 write；edit、delete、父目录删除等属于后续扩展测试，没有把它们记为新版已测结果。
- 摘要：进阶 12 验证归档与继续执行，不验证真实 LLM 摘要质量。
- 图与工具：06 执行真实文件工具，但没有挂载完整 Agent 的自动卸载与摘要中间件链。
- 外部数据库、远程沙箱、人工审批、并发压测、性能与费用消融均未部署或实测。

原理论中关于分页完整性、搜索截断、租户鉴权和生产恢复的讨论仍保留；入门路线不会要求一次完成这些工程验证。

## 6. 如何自己重新核对版本

下面的完整代码只读取已安装包的签名与路径，不会运行 Agent。

```python
from importlib.metadata import version
import inspect
from deepagents import create_deep_agent
from deepagents.backends import StateBackend, FilesystemBackend, StoreBackend, CompositeBackend
from deepagents.backends.protocol import FileData, ReadResult, WriteResult
from deepagents.middleware.filesystem import FilesystemMiddleware

print("deepagents:", version("deepagents"))
for obj in (create_deep_agent, StateBackend, FilesystemBackend,
            StoreBackend, CompositeBackend, FilesystemMiddleware,
            ReadResult, WriteResult):
    print(obj.__name__, inspect.signature(obj))
    print("source:", inspect.getfile(obj))
print("FileData fields:", FileData.__annotations__)
```

升级后优先重跑语义实验，再检查权限、异步适配和展示协议。不能只解决 import 错误就宣告迁移成功。

返回 [课程首页](../README.md)。
