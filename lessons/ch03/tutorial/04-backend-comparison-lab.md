# 04｜用三组小实验分清 Backend

你不需要一次记住所有生命周期矩阵。本节每次只改变一个条件，观察“能读到”还是“读不到”。每个 `.py` 都独立运行。

## 1. 实验 03：换会话，不换文件名

打开 [03_state_vs_filesystem.py](../code/03_state_vs_filesystem.py)。

```bash
.venv/bin/python lessons/ch03/code/03_state_vs_filesystem.py
```

两组实验都写 /note.txt，都执行三步：

```text
会话 A 写入 → 会话 A 读取 → 会话 B 读取
```

只改变 Backend，其他条件保持一致。结果为：

| Backend | A 读自己的便签 | B 读同名文件 | 原因 |
|---|---|---|---|
| StateBackend | 能 | 不能 | 文件属于各自的会话状态 |
| FilesystemBackend，共用目录 | 能 | 能 | 两个会话访问同一个磁盘文件 |

**不要记成“State 不能保存”。** 本实验中 A 的第二次调用能读到，说明同线程状态确实保存下来了；B 读不到是因为它是另一个线程。

### 代码里为什么出现 StateGraph

StateBackend 需要图运行上下文，不能在普通脚本顶层直接调用 write。为了不引入真实模型或复杂测试模型，脚本提供最小运行容器：

```text
开始 → file_step（写或读）→ 结束
```

先阅读 file_step，它只包含你在实验 01 已经见过的 write/read。建图的几行是固定运行接线，先知道它让 StateBackend 能工作即可。

### thread_id、Saver、Backend 各是什么

| 名称 | 本实验的作用 |
|---|---|
| thread_id | 会话编号 A 或 B |
| InMemorySaver | 按会话编号保存图状态，使下一次调用能继续 |
| Backend | 决定文件由 State 还是磁盘保存 |

只改会话编号不会换磁盘目录。只有 thread_id 没有 Saver，也不能自动得到会话保存服务。

### 小练习

将会话 B 的 thread_id 改成 A。预测 State 的最后一次读取也会成功；原本检查“B 不能读”的断言要同步修改。这不是隔离失效，而是你让两次请求使用了同一个会话号。

### 本实验没有证明什么

它不做性能排名，也没有做真正的进程重启测试。State 配合持久化 Saver 可恢复同线程；本实验使用 InMemorySaver，退出进程后就没有这份内存数据。

## 2. 实验 04：同一个柜子，换一个抽屉

打开 [04_store.py](../code/04_store.py)。

```bash
.venv/bin/python lessons/ch03/code/04_store.py
```

可以先把 Store 理解为柜子，namespace 理解为抽屉。代码固定使用 /preference.txt，只改变柜子或抽屉。

| 步骤 | 改变了什么 | 结果 |
|---|---|---|
| ① | Alice 写入自己的偏好 | 写入成功 |
| ② | 新 Backend 对象，柜子和抽屉不变 | 能读到 |
| ③ | 同一 Store，抽屉改为 Bob | 读不到 |
| ④ | 新 InMemoryStore，抽屉仍叫 Alice | 读不到 |

所以三个对象不能混为一谈：Store 是数据容器，StoreBackend 是文件访问接口，namespace 是该容器内的分区。

代码中的 namespace 是一个返回元组的函数。`("alice",)` 最后的逗号表示单元素元组；本实验没有依赖动态身份，不必先学习 Runtime。

### 与 State 的区别

StateBackend 从当前线程状态取文件；StoreBackend 从指定 Store 和 namespace 取文件。后者不会仅因更换 thread_id 就隔离文件，因此适合跨任务复用用户偏好。

本脚本直接测试存储层，不经过线程图。它实际证明的是“同 Store/namespace 共享”和“不同 namespace 隔离”，没有把对象重建冒充跨进程恢复。

### 小练习

让 Bob 的 Backend 也使用 Alice 的 namespace，就会读到 Alice 的偏好。于是可以理解：隔离不是由变量名 bob 决定的。

生产服务的 namespace 应来自可信身份，同时还要校验线程访问权；这些是后续工程知识，不是本脚本自动实现的能力。

## 3. 实验 05：按地址分发到不同保管员

打开 [05_composite.py](../code/05_composite.py)。

```bash
.venv/bin/python lessons/ch03/code/05_composite.py
```

先只配置一条规则：

```text
/memories/ 开头 → StoreBackend
其余路径       → FilesystemBackend
```

这样不需要再加入 StateGraph，就能直接看到路由效果。

| 外部写入路径 | 由谁保存 | 应观察到什么 |
|---|---|---|
| /draft.txt | 磁盘 | output/05_composite/draft.txt 存在 |
| /memories/preference.txt | Store | 磁盘没有这个文件，但 router 可以读到 |

代码中的 default 是默认收件人，routes 是指定前缀的分拣规则。Composite 自己不是新的磁盘或数据库。

### 为什么 Store 内部路径变短了

外部路径 /memories/preference.txt 匹配路由后，前缀 /memories 被去掉，Store 收到 /preference.txt。因此直接访问 Store 时要用内部路径；通过 router 访问时继续使用外部完整路径。

### 小练习

将路由前缀改为 /profiles/，对应读写路径也一起修改。不要只改字典中的规则，否则旧的 /memories/ 路径会交给默认后端。

更复杂的“默认 State + 长期 Store”只是组合变化，路由原理相同。需要注意：InMemoryStore 仍在内存中，加上 Composite 并不会让它具备抗重启能力。

## 4. 现在再看总表

| 组件 | 文件在哪里 | 哪个条件决定是否共享 |
|---|---|---|
| StateBackend | 图状态 | 线程状态，以及保存/恢复方式 |
| FilesystemBackend | 磁盘 | 实际访问的目录和路径 |
| StoreBackend | Store | 同一份 Store 数据 + namespace |
| CompositeBackend | 目标后端 | 路由规则和目标后端的作用域 |

无需此时学习性能百分位、并发锁和数据库迁移。先把每种组件在这三组实验中做的事说清楚，再阅读生产设计。

## 5. 基础验收与下一步

- [ ] 我能在运行前预测 State 与 Filesystem 的 A/B 读取结果。
- [ ] 我能解释更换 Backend 对象为什么不等于清空磁盘或 Store。
- [ ] 我知道 namespace 相同但 Store 不同，仍可能读不到。
- [ ] 我能判断一个路径是否命中 Composite 路由。
- [ ] 我不把 InMemorySaver/InMemoryStore 写成抗进程重启的数据库。

回到 [文件工具实验说明的实验 06](03-file-tools-lab.md)，理解这些后端如何被 Agent 工具调用。完整理论可查 [工具与 Backend 语义](02-tools-and-backends.md)。
