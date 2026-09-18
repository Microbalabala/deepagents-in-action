"""实验 01：文件到底存在哪里？

运行：.venv/bin/python lessons/ch03/code/01_filesystem.py
不需要模型、API Key，也不需要先运行其他实验。
观察重点：虚拟路径 /note.txt 对应磁盘上的哪个真实文件。
"""

from pathlib import Path

from deepagents.backends import FilesystemBackend


def main():
    # __file__ 是当前 py 文件的位置，所以从任何工作目录运行，输出位置都一样。
    # 每个实验使用自己的 output 子目录，避免相互覆盖。
    folder = Path(__file__).resolve().parent / "output" / "01_filesystem"
    folder.mkdir(parents=True, exist_ok=True)

    # Backend 可以理解为“保管文件的人”。FilesystemBackend 把文件保存在磁盘。
    # virtual_mode=True：/note.txt 从 folder 开始算，不是电脑根目录下的文件。
    backend = FilesystemBackend(root_dir=folder, virtual_mode=True)

    print("\n① 创建文件：backend.write('/note.txt', ...)")
    written = backend.write(
        "/note.txt", "我的第一份学习笔记：Backend 决定文件存在哪里。"
    )
    # error 为 None 表示没有错误。检查结果，比只打印“写好了”更可靠。
    assert written.error is None, written.error
    print("写入成功。")

    print("\n② 通过 Backend 读取")
    result = backend.read("/note.txt")
    assert result.error is None, result.error
    # read 返回一个结果对象；真正的文本在 file_data['content'] 中。
    print(result.file_data["content"])

    print("\n③ 找到电脑上的真实文件")
    real_file = folder / "note.txt"
    print("虚拟路径：/note.txt")
    print("真实路径：", real_file)
    print("磁盘内容：", real_file.read_text(encoding="utf-8"))

    print("\n④ 换一个 Backend 对象，仍然使用同一个目录")
    another_backend = FilesystemBackend(root_dir=folder, virtual_mode=True)
    again = another_backend.read("/note.txt")
    assert again.error is None, again.error
    print("仍然读到：", again.file_data["content"])

    print("\n记住：FilesystemBackend 的文件在磁盘里，不在 backend 这个变量里。")
    print("练一练：修改 write 的内容后重新运行，再打开上面的真实文件。")


if __name__ == "__main__":
    main()
