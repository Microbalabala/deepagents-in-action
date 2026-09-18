# 02｜七种工具、存储后端与版本语义

本节的精确行为以本项目安装的 `deepagents==0.7.14` 为准。代码实验在下一节统一给出，这里先解释每个参数背后的契约。

## 1. 工具接口与 Backend 接口不是同一层

| 面向模型的工具 | Backend 方法 | 核心行为 |
|---|---|---|
| `ls(path)` | `ls(path)` | 查看目录下的条目 |
| `read_file(file_path, offset, limit)` | `read(file_path, offset, limit)` | 分页读取内容 |
| `write_file(file_path, content)` | `write(file_path, content)` | 创建或完整覆盖 |
| `edit_file(file_path, old_string, new_string, replace_all)` | `edit(...)` | 精确字符串替换 |
| `delete(file_path)` | `delete(file_path)` | 删除文件或递归删除目录 |
| `glob(pattern, path)` | `glob(pattern, path)` | 匹配文件路径 |
| `grep(pattern, path, glob, output_mode, max_count)` | `grep(pattern, path, glob, max_count=...)` | 字面量搜索，再由工具层选择展示模式 |

在代码里直接调用 `read_file(...)` 的教学片段，通常是在描述工具调用，不代表从 `deepagents` 导入了同名普通函数。本文的实际实验通过 Agent 的工具调用链执行，避免混淆这一点。

## 2. `ls`：导航，不是“读取全部内容”

`ls` 适合确认目录存在什么、寻找下一步要搜索的范围。Backend 返回 `LsResult.entries` 中的文件信息，但模型看到的工具文本可能只是路径列表；不能假定一定展示所有元数据。

空结果通常是正常情况。需要区分：空目录、无匹配文件、没有权限、存储不可用，这四种状态不能全部解释成“资料不存在”。

更好的查询路径是先列 `/sources/`，再在相关子目录搜索，而不是在所有用户所有任务的数据上全局扫描。

## 3. `read_file`：分页是一种正确性约束

### 3.1 偏移量从 0 开始

`offset=100, limit=50` 请求的是第 101 行开始的最多 50 行，不是从第 100 行开始。这里的单位通常是文本源行，不是字节、字符或 token。

当前工具默认 `limit=100`；Backend `read` 方法通常默认 `limit=2000`。同样的文件，直接调用 Backend 和通过工具调用，默认读取范围可能不同。因此实验中显式传入分页参数。

### 3.2 结构化分页字段

```text
ReadResult
  error         失败原因，成功时为 None
  file_data     当前返回的文件内容与编码
  total_lines   可确定时的源文件总行数
  start_line    本页第一行，1 基
  end_line      本页最后一行，1 基
  next_offset   下一页偏移量，0 基；没有下一页时通常为 None
```

第 2–3 行返回后，下一页 `offset=3`。数字等于上一页 `end_line`，因为两个字段的编号基准不同。

`0.7.14` 的实际工具输出可类似：

```text
@@ lines 2-3 of 4 | next offset 3 @@
beta
TODO x
```

不要写死“每一行前一定有行号和 Tab/两个空格”。展示协议在版本间发生过变化。应用需要稳定解析时，优先使用结构化 Backend 结果。

### 3.3 行数上限不等于 token 上限

一行压缩 JSON 就可能非常大。中间件还可能对长结果进行字符预算限制。即使 `limit=20`，也不能保证模型一定收到完整的 20 行。需要结合分页提示、截断说明和源文件结构判断。

实用方式是把大型资料按章节、记录或语义单元组织成文件，避免把几十兆文本存成一个不可导航的单行文件。

### 3.4 多模态读取的边界

当前实现可以根据编码与媒体类型返回图像、音频、文件等内容块；视频还涉及可选的帧提取支持。**能返回内容块，不意味着任意模型/供应商都能接受和理解该格式。**

需要检查四件事：Backend 能否传输二进制；中间件能否识别类型；模型适配器能否转换内容块；模型是否支持该模态和尺寸。PDF/PPT 支持也不能被当作通用 OCR、版面解析、表格抽取准确率保证。

文本文件的行分页与视频的时间采样语义不同。不要把文本实验中的 `offset` 推广为所有媒体的“第几行”。大型媒体还会引入 base64 体积、上传限额和内存开销。

## 4. `write_file`：在当前版本是覆盖写

```text
原内容：A\nB\n
write_file(path, "C\n")
新内容：C\n
```

它不是 append，也不是“文件存在则一定失败”。如果只需要改一处，使用 `edit_file`；如果要追加且没有专用追加能力，需要读出、拼接、写回，但这种做法在并发场景会发生丢失更新。

写入成功不自动等价于：事务提交、跨副本可见、备份完成或断电不丢。不同后端有不同耐久性保证。框架层的 `WriteResult` 不能替代数据库或文件系统的持久化规范。

## 5. `edit_file`：精确替换与歧义处理

`old_string` 是字面量，不是正则表达式。默认 `replace_all=False`，若同一个旧字符串出现多次，通常返回错误，要求提供更明确的上下文。

例如文件同时出现两次 `timeout=30`。如果只改客户端配置，应提供包含段落标题的完整旧片段，而不是打开 `replace_all=True` 把所有超时都改掉。

常见失败来源：换行符不同、缩进不同、正文已被其他任务修改、旧片段根本不存在。正确的恢复流程是重新读取相关范围，确认当前版本，再生成新的精确替换。不要无限重试旧参数。

## 6. `delete`：目录删除会影响后代路径

删除 `/scratch/` 意味着清理该目录及其后代，不只是删除一个目录标记。因此权限需要覆盖祖先目录删除；仅禁止写 `/policies/rules.md`，却允许通过另一个接口删除整个父目录，是典型设计漏洞。

当前内置后端支持删除，但自定义后端如果没有实现该能力，不能假设 Agent 一定会获得可用的 `delete`。对历史版本的包装器升级时，也必须加入删除路径的处理。

这里的删除不会自动抹除旧检查点、备份、审计记录或对象历史版本。业务中的数据删除要求，需要跨所有副本和保留层设计。

## 7. `glob` 与 `grep`：找名字和找内容

### 7.1 `glob` 找路径

当前实现支持常见的 `*`、`**`、`?`、字符集合与部分组合模式，但不能把它无条件等同于 shell glob、Python glob 或 Gitignore。

在 `0.7.14` 中，无斜杠模式 `*.md` 会在搜索根下按文件名匹配；含斜杠模式按相对路径匹配。点文件/点目录有特殊规则，`**` 不会自动遍历所有隐藏目录。涉及隐藏文件或路由前缀时应建立独立测试。

`glob` 的结果也可能截断。返回 100 个文件不是“系统总共只有 100 个文件”的证明。

### 7.2 `grep` 找字面量

搜索 `a.b` 匹配文本 `a.b`，不会按正则匹配 `axb`。搜索 `foo|bar` 是寻找带竖线的原文，不是“foo 或 bar”。需要多个关键词时，可以分别搜索并在应用层合并结果。

| `output_mode` | 返回信息 | 使用时机 |
|---|---|---|
| `files_with_matches` | 有匹配的路径 | 先定位候选文件 |
| `content` | 匹配内容与位置 | 找到应读取的证据窗口 |
| `count` | 每文件匹配记录数 | 了解分布，不代替业务实体计数 |

同一行出现三次关键词，通常仍是一条匹配行，不能据此推算出现三次。若结果截断，计数也只能代表已返回的部分。

工具默认匹配预算为 1,000，可通过参数或中间件配置调整。提高上限会增加扫描和上下文成本，不是越大越好。实际完整性应结合 `truncated`、后端预算和搜索范围判断。

### 7.3 搜索结果为空的正确解释

空结果只能证明“本次查询，在可见范围和当前查询语义下，没有返回匹配”。可能原因包括不同措辞、权限过滤、路径错误、编码差异、文件还未写入，以及资料确实不存在。研究 Agent 应明确查询范围，不能把“没搜到”提升成全局事实判断。

## 8. Backend 全景对比

| 后端 | 数据载体 | 跨线程 | 抗进程重启 | Shell | 核心用途 |
|---|---|---|---|---|---|
| StateBackend | Graph State 的 `files` | 默认隔离 | 取决于 Checkpointer/状态恢复 | 无 | 临时证据、任务草稿 |
| FilesystemBackend | 磁盘文件 | 共享同一 root 时可见 | 取决于磁盘/卷生命周期 | 无 | 专用本地工作目录 |
| StoreBackend | LangGraph Store | 同 namespace 可见 | 取决于 Store 实现 | 无 | 跨会话偏好与资料 |
| CompositeBackend | 路由到多个后端 | 取决于命中路由 | 取决于命中路由 | 取决于默认后端能力 | 分层生命周期 |
| LocalShellBackend | 宿主机文件与进程 | 取决于目录 | 取决于磁盘 | 有 | 受控本地开发 |
| 沙箱后端 | 隔离环境内的文件与进程 | 取决于实例设计 | 取决于卷和实例生命周期 | 有 | 需要执行代码的任务 |

### 8.1 StateBackend：对象不等于状态容器

`StateBackend()` 是无参实例，操作时从当前 LangGraph 执行上下文读取/更新 `files`。因此直接在普通 Python 顶层调用 `StateBackend().write(...)` 会报缺少图上下文。

本版本通过图通道发送文件更新，`WriteResult`/`EditResult` 不再包含旧资料中的 `files_update` 字段。无需手工把这个字段塞回 State。

`FileData` 的核心形态为：

```python
file_data = {
    "content": "第一行\n第二行\n",
    "encoding": "utf-8",
    # created_at / modified_at 是可选元数据
}
```

不要继续使用旧示例中按行列表存储 `content` 的格式。

### 8.2 FilesystemBackend：逻辑路径映射到真实文件

```python
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(
    root_dir="/专门的实验临时目录",
    virtual_mode=True,
)
```

`/notes/a.md` 被映射到根目录下的 `notes/a.md`。本地 `0.7.14` 的 `virtual_mode` 默认已经是 `True`；本文仍显式填写，便于审阅。

**路径限制不等于进程沙箱。** 它约束相应文件操作的路径映射，不能给任意自定义 Python 工具或宿主机 Shell 提供隔离。`virtual_mode=False` 下，绝对路径不受 `root_dir` 作为访问边界的保护。

### 8.3 StoreBackend：namespace 决定共享范围

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

backend = StoreBackend(
    store=InMemoryStore(),
    namespace=lambda _runtime: ("ch03", "local-user"),
)
```

这段可用于独立的 Backend 调用，因为 Store 显式传入且 namespace 不读取 Runtime。如果 namespace 依赖运行时身份，应该在图内使用，并由可信服务端提供上下文。

生产中通常使用 `(tenant_id, user_id, "files")` 等命名空间。把 namespace 写死为一个全局常量只是单用户实验技巧，不能直接复用到多租户服务。

### 8.4 CompositeBackend：最长前缀、去前缀、恢复前缀

设 `/memories/` 路由到 Store：

```text
/scratch/a.md          → default，收到 /scratch/a.md
/memories/user.md      → Store，收到 /user.md
/memories/team/x.md    → 更长的 /memories/team/ 路由优先（若配置）
```

Backend 返回路径后，Composite 会按场景补回公开前缀。它是一种路由器，不是多存储事务协调器、缓存一致性协议或访问授权系统。

全局 `ls`、`glob`、`grep` 可能需要聚合多个后端。其耗时、失败和完整性都取决于所有参与后端。生产代码不能默认“某一个后端成功就是全局成功”。

### 8.5 Shell 与沙箱

LocalShellBackend 提供命令执行，但命令运行在宿主机上，`root_dir` 作为工作目录不意味着命令不能越界。最小 `PATH` 也不构成安全隔离。

沙箱要同时考虑进程权限、文件系统、网络、凭证、资源配额和生命周期。沙箱内默认允许外网仍然可能发生数据外传；沙箱被销毁也不代表外部存储中的产物被删除。

## 9. 自定义协议应保证什么

`BackendProtocol` 的同步方法有相应异步入口；默认实现可能将同步方法卸载到线程。远程 I/O 服务应优先提供真正的异步实现，避免阻塞事件循环或耗尽线程池。

结果类型包含 `LsResult`、`ReadResult`、`WriteResult`、`EditResult`、`DeleteResult`、`GrepResult`、`GlobResult`。另外还有文件上传/下载能力，常用于应用侧传输二进制，不等同于模型逐字输出文件内容。

接口形状一致还不够，需要测试路径规范化、编码、覆盖、目录删除、搜索边界、分页连续性、失败传播和 async 行为。完整的适配器必须有“语义契约”，否则更换后端就可能悄悄改变业务结果。

## 10. 版本迁移速查

| 旧资料中可能出现的写法 | 本课程采用的写法 |
|---|---|
| `backend=lambda rt: StateBackend(rt)` | `backend=StateBackend()` |
| `StoreBackend()` 无 namespace | 显式 `namespace=lambda rt: (...)` |
| `WriteResult(files_update=...)` | 本版本没有该字段；State 更新由后端完成 |
| `FileData.content` 为行列表 | 本版本为字符串，并声明 encoding |
| `write_file` 只创建不覆盖 | 本版本创建或完整覆盖 |
| 只有六种文件工具 | 还需要学习 `delete` |
| 读取结果固定逐行编号 | 根据当前结构化分页/展示协议处理 |

下一节：[完整文件工具实验](03-file-tools-lab.md)。参考 [官方后端说明](https://docs.langchain.com/oss/python/deepagents/backends) 可了解整体设计，但上表以本地版本源码为准。
