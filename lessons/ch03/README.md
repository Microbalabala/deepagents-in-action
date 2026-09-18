# 第 3 章：先运行，再理解虚拟文件系统

**新版实验日期：2026-09-18；基线：Python 3.12、deepagents 0.7.14。**

这一版从简单现象入手：创建一张便签，看看它在哪；换个会话，看看还能不能读到。先用小实验认识组件，再阅读深入原理。

所有实验都是独立 `.py` 文件，不用 Notebook，不需要复制公共代码，也不依赖之前脚本留下的变量。每个脚本有中文注释，运行时按“操作 → 结果 → 结论”打印。源码位于 `code/`，讲解位于 `tutorial/`，沿用你整理后的目录。

## 1. 先花十分钟看两个现象

在项目根目录打开终端，运行：

```bash
.venv/bin/python lessons/ch03/code/01_filesystem.py
```

你会看到一段笔记和它在电脑上的真实路径。打开该文件，确认它确实存在。

然后运行：

```bash
.venv/bin/python lessons/ch03/code/03_state_vs_filesystem.py
```

你会直接看到：

```text
                             A 读取     B 读取
StateBackend                 能         不能
FilesystemBackend（同目录）   能         能
```

先记住：**Backend 决定文件存在哪里；更换会话号不会自动更换磁盘目录。**

## 2. 基础学习路线：只看这六个脚本

| 顺序 | 文件 | 本次只回答什么 | 建议用时 |
|---|---|---|---:|
| 01 | [01_filesystem.py](code/01_filesystem.py) | 虚拟路径对应电脑上的哪个文件？ | 5 分钟 |
| 02 | [02_file_operations.py](code/02_file_operations.py) | 如何读、写、改、删、找文件？ | 10 分钟 |
| 03 | [03_state_vs_filesystem.py](code/03_state_vs_filesystem.py) | 同一便签换个会话还能看到吗？ | 10 分钟 |
| 04 | [04_store.py](code/04_store.py) | Store 和 namespace 分别负责什么？ | 5–10 分钟 |
| 05 | [05_composite.py](code/05_composite.py) | 如何按路径把文件交给不同后端？ | 5–10 分钟 |
| 06 | [06_file_tools.py](code/06_file_tools.py) | Backend 方法怎样变成 Agent 文件工具？ | 10 分钟 |

**前六个实验都不需要 API Key，不调用大模型。** 实验 03 完成 State 与 Filesystem 的同条件对比；实验 06 真正执行七种文件工具，满足本章基础实验要求。

运行方式始终相同，例如：

```bash
.venv/bin/python lessons/ch03/code/04_store.py
```

详细步骤、输出解读与练习见 [文件操作实验说明](tutorial/03-file-tools-lab.md) 和 [Backend 对比实验说明](tutorial/04-backend-comparison-lab.md)。

## 3. 先用一句话认识组件

| 组件 | 可以先怎样理解 | 需要记住的边界 |
|---|---|---|
| Backend | 文件保管员 | 决定文件放在哪里 |
| FilesystemBackend | 电脑上的文件夹 | 相同目录可被多个会话访问 |
| StateBackend | 每个会话自己的便签区 | 多轮保存需要 Saver 或显式传递状态 |
| Checkpointer / Saver | 按会话号保存图状态的柜子 | InMemorySaver 只存在于当前进程 |
| StoreBackend | 把 Store 里的数据当文件访问 | 它不是 Store 本身 |
| namespace | 同一个 Store 中的不同抽屉 | 同名抽屉放在不同 Store 中并不共享数据 |
| CompositeBackend | 按路径分拣的分拣员 | 自己不提供新的存储介质 |
| 文件工具 | Agent 使用的操作入口 | read_file 工具内部调用 Backend 的 read |
| Permission | 操作门口的检查规则 | 不等于整个电脑的安全沙箱 |

## 4. 看懂基础之后，再选学

| 文件 | 内容 | 是否请求真实模型 |
|---|---|---|
| [07_real_agent.py](code/07_real_agent.py) | 模型读取一份笔记、保存一份总结 | 是，需要现有配置 |
| [08_large_result.py](code/08_large_result.py) | 长工具结果变成文件引用与预览 | 否，使用框架测试模型 |
| [09_permissions.py](code/09_permissions.py) | 规则文件禁止写，草稿允许写 | 否，使用框架测试模型 |

08、09 中的固定模型只负责发出预先写好的工具请求；文件工具与中间件执行是真实的。它们不是基础实验的前置要求。

原有深入内容保留在进阶区，避免和入门流程混在一起：

- [审计包装器](code/advanced/10_audit_backend.py)：不改变存储，给操作增加记录。
- [版本条件更新](code/advanced/11_optimistic_concurrency.py)：阻止过期内容覆盖新内容。
- [摘要归档](code/advanced/12_summarization.py)：观察原始对话的保存位置。
- [完整研究报告](code/advanced/13_research_report.py)：真实模型、证据索引与产物校验；需要模型配置。

进阶实验也独立运行，不依赖基础脚本的变量。例如：

```bash
.venv/bin/python lessons/ch03/code/advanced/11_optimistic_concurrency.py
```

## 5. 输出在哪，重复运行会怎样

磁盘实验把文件保存在各自的 `code/output/实验目录/`，程序结束后仍可打开；输出目录已加入本目录的忽略规则。脚本会重建或覆盖自己使用的教学文件，07、09 还会清理指定的旧输出，避免误判本次运行成功。

State、InMemoryStore 中的文件不一定存在于磁盘；这是组件差异的一部分。进程退出后，内存版 Saver/Store 的数据不会保留。进阶审计实验使用临时目录，完整报告会把通过校验的最终产物导出到 `code/output/13_research_report/`。

所有脚本都使用项目已有环境，不需要升级依赖。请在项目根目录运行给出的命令；也可以在编辑器中选择项目 `.venv/bin/python` 解释器后运行文件。

## 6. 理论讲义目录

| 讲义 | 什么时候阅读 |
|---|---|
| [01：概念与运行机制](tutorial/01-concepts-and-architecture.md) | 跑过实验后，理解上下文、State 与检查点 |
| [02：工具与 Backend 语义](tutorial/02-tools-and-backends.md) | 查询参数、边界与版本差异 |
| [03：文件操作实验说明](tutorial/03-file-tools-lab.md) | 配合脚本 01、02、06 |
| [04：Backend 对比实验说明](tutorial/04-backend-comparison-lab.md) | 配合脚本 03、04、05 |
| [05：上下文管理](tutorial/05-context-engineering-lab.md) | 理解自动卸载与摘要 |
| [06：生产设计与扩展](tutorial/06-production-and-customization.md) | 权限、审计、并发与故障恢复 |
| [07：综合研究任务](tutorial/07-capstone-research-agent.md) | 先完成简单模型接入，再做完整报告 |
| [08：面试与练习](tutorial/08-interview-and-exercises.md) | 巩固原理与系统设计 |
| [09：来源与验证记录](tutorial/09-references-and-validation.md) | 核对版本和实际测试范围 |

每次学完一个实验，只回答三件事：**它操作了什么？数据放在哪？换掉哪个条件会改变结果？** 暂时不必把所有类和参数一起记住。
