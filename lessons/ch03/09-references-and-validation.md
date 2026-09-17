# 09｜来源索引、版本差异与验证记录

核对日期：2026-09-17。讲义采用“本项目锁定环境 → 安装源码 → 实际执行结果”的证据顺序。网络资料用于主题覆盖和背景核对，不能覆盖本地版本的相反证据。

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

## 4. 实验验证记录

验证使用本项目已有 `.venv/bin/python`，将 Markdown 中标注 `# runnable:` 的代码直接提取到内存并执行。没有在项目新增 `.py` 文件；磁盘实验使用系统临时目录。

| 实验 | 验证内容 | 结果 |
|---|---|---|
| 公共驱动 | 测试模型、图、工具结果提取 | 通过 |
| A | 七种工具、覆盖、歧义编辑、目录删除 | 通过 |
| B | 字面量 grep、匹配行计数 | 通过 |
| C | 完整分页、搜索数量限制和 truncated | 通过 |
| D | 三种 Backend、同/跨线程、Agent/Saver 重建 | 通过 |
| E | 同用户共享、不同用户/租户 namespace 隔离 | 通过 |
| F | Composite 分流、聚合、前缀移除 | 通过 |
| F 扩展 | 最长路由前缀优先 | 通过 |
| G | 两个独立进程间复用同一磁盘根目录 | 通过 |
| H | 工具大结果卸载、内容一致、关键证据回读 | 通过 |
| I | 固定摘要模型触发归档并继续执行 | 通过 |
| J | 写/编辑/删除拒绝与路径校验 | 通过 |
| J 扩展 | first-match-wins 权限顺序 | 通过 |
| K | 审计包装器同步/异步入口 | 通过 |
| L | 版本条件更新阻止过期覆盖 | 通过 |

这相当于 **1 个公共驱动代码块 + 14 个实验代码块**。这些实验测试真实框架与存储行为；固定模型只负责产生确定的请求，不模拟文件工具执行结果。

交付前另检查了全部 20 个 Python 围栏代码块的语法、10 份 Markdown 的围栏配对，以及 32 处本地文件/文档链接的目标存在性。真实模型单元只做语法检查，未在这些离线实验中执行。

### 4.1 关键实测输出

```text
Backend | 同线程 | 不同线程 | 新Agent共享Saver | 新Agent新Saver
State | success | error | success | error
Filesystem | success | success | success | success
Store | success | success | success | success
```

```text
文本分页：1–5 → 6–10 → 11–12
grep max_count=3：3 个匹配，truncated=True
大工具结果：37,084 字符 → 1,255 字符的替代工具消息
完整原文仍在 Backend，中间证据 cache_ttl_seconds=37 回读成功
```

卸载路径中含随机调用标识；将来版本、预览规则或配置变化会影响替代消息长度。这些数字描述本次受控实验，不代表真实模型通用的压缩率或成本节省。

### 4.2 验证过程中纠正的问题

逐页返回内容可能包含尾部换行，如果将页面简单用额外换行拼接，会引入空行。本课程改成逐页 `splitlines()` 后累计源行，以验证源行顺序和覆盖。它不是二进制或换行编码无损恢复算法；需要无损文件传输时使用下载接口或相应底层读取。

## 5. 本次没有实际执行的部分

- 第 07 部分的真实模型调用：提供完整接入代码与独立验收，做语法检查，未调用模型 API。
- 外部持久化 Checkpointer/Store：提供恢复实验设计，未部署 PostgreSQL 或外部服务。
- 沙箱服务与 LocalShell 执行：讲解边界，未启动远程沙箱或让 Agent 执行宿主 Shell。
- 人工审批恢复：解释机制与所需状态，未连接审批界面。
- 百万文件性能、真实 token 费用、LLM 质量消融与生产并发压测：属于进阶作业，未编造结果。

这些限制不影响第 03、04 部分基本实验的完成。它们用于明确“可运行课程代码”和“已经替你调用外部服务”之间的区别。

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

返回 [课程首页](README.md)。
