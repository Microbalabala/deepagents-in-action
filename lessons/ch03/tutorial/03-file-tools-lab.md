# 03｜新手文件操作实验：一张便签、一份购物清单

本节只使用独立 `.py` 文件。打开脚本看注释，在终端运行，看输出，再修改一个参数。无需复制代码块，也不需要任何公共实验驱动。

## 1. 准备：确认使用项目的 Python

终端切换到项目根目录后运行：

```bash
.venv/bin/python -c "from importlib.metadata import version; print(version('deepagents'))"
```

本讲义验证环境为 `0.7.14`。不要为了运行这些实验先升级整个项目。如果出现 `ModuleNotFoundError`，首先确认是否误用了系统 Python，而不是项目的 `.venv/bin/python`。

编辑器中运行时，也要选择这个解释器。全部脚本有 `if __name__ == "__main__"` 入口，直接运行即可。

## 2. 实验 01：创建文件，再到电脑上找到它

打开 [01_filesystem.py](../code/01_filesystem.py)。

```bash
.venv/bin/python lessons/ch03/code/01_filesystem.py
```

### 先预测

代码写入 `/note.txt`，它会出现在电脑根目录吗？换一个 Backend 对象，文件会消失吗？

### 观察四步

1. backend.write 保存一句学习笔记。
2. backend.read 读出同一句话。
3. 输出真实路径，打开它确认内容。
4. 新建 Backend 对象，使用相同根目录，仍然能读到。

实际路径是：

```text
lessons/ch03/code/output/01_filesystem/note.txt
```

`root_dir` 是文件根目录；`virtual_mode=True` 表示 `/note.txt` 相对于这个根目录。它并没有在电脑的 `/` 下创建文件。

### 只看这三个 API

| 代码 | 作用 |
|---|---|
| FilesystemBackend(root_dir=folder, virtual_mode=True) | 选择保管文件的磁盘目录 |
| backend.write("/note.txt", text) | 写入正文 |
| backend.read("/note.txt") | 返回读取结果对象 |

读取结果不是普通字符串。先看 `result.error` 是否为 `None`，再从 `result.file_data["content"]` 取出正文。

脚本中的 `assert` 是检查点：“如果实际结果不满足预期，就停下来提醒我。”它不是文件系统组件，可以先按注释理解。

### 小练习

只修改笔记内容后重跑。真实文件内容也应改变。由此记住：文件保存在磁盘中，不是保存在 backend 变量中。

## 3. 实验 02：用购物清单理解读写改删

打开 [02_file_operations.py](../code/02_file_operations.py)。

```bash
.venv/bin/python lessons/ch03/code/02_file_operations.py
```

清单最初只有三行：苹果、牛奶、面包。每个操作都使用这份小文件，不引入研究报告、复杂 JSON 或抽象任务脚本。

| 步骤 | 操作 | 应看到什么 |
|---|---|---|
| ① | write 创建 | 初始三行清单保存成功 |
| ② | ls 列目录 | /shopping.txt |
| ③ | read 全文 | 苹果、牛奶、面包 |
| ④ | offset=1，limit=1 | 只读到牛奶；下一偏移量为 2 |
| ⑤ | edit 替换 | 牛奶变成豆浆 |
| ⑥ | glob 查文件名 | 找到 .txt 文件 |
| ⑦ | grep 查正文 | 找到第 2 行的豆浆 |
| ⑧ | write 同一路径 | 全文变成“只买茶叶” |
| ⑨ | delete 临时文件 | 再读临时文件时返回找不到 |

### 三组区别

**read 与分页 read：** offset 从 0 开始，limit 表示最多多少行。offset=1 是第二行，不是第一行。

**write 与 edit：** 本版本 write 是整份覆盖，edit 是精确替换一个片段。不要用 write 当作追加。

**glob 与 grep：** glob 找名字，grep 找正文。寻找所有 .txt 文件用 glob；寻找“豆浆”出现在哪用 grep。

### 小练习

先只改 offset 为 0，预测读取结果从牛奶变成苹果。原断言仍要求牛奶，因此会失败；将断言预期同步改为苹果再运行。这样能体会“检查条件必须跟实验条件一致”。

然后只改 grep 的词为“可乐”，观察空匹配。没有匹配与操作报错是不同情况。

## 4. 实验 06：让同样的动作走真实文件工具

先做完实验 03–05 认识 Backend，再回来看 [06_file_tools.py](../code/06_file_tools.py)。

```bash
.venv/bin/python lessons/ch03/code/06_file_tools.py
```

前面的代码由你直接调用 Backend。这次走的是：

```text
手写工具请求 → ToolNode 执行文件工具 → Backend → ToolMessage 返回
```

例如 read_file 是工具名，内部调用的是 Backend 的 read 方法。你会看到同一份购物清单，同时看到工具名称、参数、状态和返回内容。

### 这里新增的三个概念

| 名字 | 暂时这样理解即可 |
|---|---|
| FilesystemMiddleware | 提供 ls、read_file 等文件工具 |
| AIMessage.tool_calls | 一张“要执行什么、参数是什么”的请求单 |
| ToolNode | 根据请求单执行工具的执行器 |

请求单由代码手工填写，因此没有 API Key，也没有模型随机性。它没有模拟工具结果：七种文件工具都真实运行，文件也真实保存在磁盘。

图只包含“开始 → tools → 结束”。暂时不需要学习规划、多 Agent、公共驱动或测试模型。后面的真实模型实验只是让模型负责填写请求单。

### 预期输出示例

```text
调用 read_file，参数：{'file_path': '/shopping.txt', 'offset': 1, 'limit': 1}
状态：success
结果：@@ lines 2-2 of 3 | next offset 2 @@
牛奶
```

最后一次读取已删除文件，会显示 error。这是刻意安排的观察：执行器会把失败反馈出来，不能把它当作整个课程未运行成功。

本脚本只挂载工具执行节点，没有完整 Agent 的自动卸载和摘要调用链。理解工具之后，再通过选学实验 08 观察中间件处理大结果。

## 5. 最小验收

- [ ] 我能打开实验 01 在磁盘上生成的文件。
- [ ] 我能解释 offset=1 为什么读到第二行。
- [ ] 我能区分覆盖写、局部替换、文件名搜索和正文搜索。
- [ ] 我运行了实验 06，实际执行七种文件工具。
- [ ] 我知道 success/error 来自工具结果，不是模型自己宣称成功。

继续：[Backend 对比实验](04-backend-comparison-lab.md)。返回：[学习首页](../README.md)。
