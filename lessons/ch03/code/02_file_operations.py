"""实验 02：用一份购物清单认识文件操作。

运行：.venv/bin/python lessons/ch03/code/02_file_operations.py
这里直接调用 Backend 方法；实验 06 再把同样的动作变成 Agent 文件工具。
"""

from pathlib import Path

from deepagents.backends import FilesystemBackend


def main():
    folder = Path(__file__).resolve().parent / "output" / "02_operations"
    folder.mkdir(parents=True, exist_ok=True)
    backend = FilesystemBackend(root_dir=folder, virtual_mode=True)

    print("\n① write：创建购物清单")
    # 当前 0.7.14 中，write 会创建文件；文件已存在时，会完整覆盖。
    # 因此重复运行实验，会重新得到相同的初始清单。
    result = backend.write("/shopping.txt", "苹果\n牛奶\n面包")
    assert result.error is None, result.error

    print("\n② ls：看看目录里有什么")
    listing = backend.ls("/")
    assert listing.error is None, listing.error
    for entry in listing.entries:
        print(entry["path"])

    print("\n③ read：读取整份清单")
    whole = backend.read("/shopping.txt")
    assert whole.error is None, whole.error
    print(whole.file_data["content"])

    print("\n④ 分页 read：只读取第 2 行")
    # offset 从 0 开始：0 是第一行，1 是第二行；limit 是最多读取的行数。
    page = backend.read("/shopping.txt", offset=1, limit=1)
    assert page.error is None, page.error
    print("本页内容：", page.file_data["content"].strip())
    print("下一页 offset：", page.next_offset)
    assert page.file_data["content"].strip() == "牛奶"

    print("\n⑤ edit：把牛奶换成豆浆")
    edited = backend.edit("/shopping.txt", old_string="牛奶", new_string="豆浆")
    assert edited.error is None, edited.error
    print(backend.read("/shopping.txt").file_data["content"])

    print("\n⑥ glob：按文件名找所有 txt 文件")
    found_files = backend.glob("*.txt", path="/")
    assert found_files.error is None, found_files.error
    for entry in found_files.matches:
        print(entry["path"])

    print("\n⑦ grep：按正文找“豆浆”在哪一行")
    # grep 搜正文；glob 搜文件名。这是二者最重要的区别。
    found_text = backend.grep("豆浆", path="/")
    assert found_text.error is None, found_text.error
    for match in found_text.matches:
        print(match)

    print("\n⑧ 再次 write：观察它是覆盖，不是追加")
    assert backend.write("/shopping.txt", "只买茶叶").error is None
    overwritten = backend.read("/shopping.txt").file_data["content"]
    print(overwritten)
    assert overwritten == "只买茶叶"

    print("\n⑨ delete：删除一个专门用于练习的临时文件")
    assert backend.write("/remove_me.txt", "这份文件可以删除").error is None
    assert backend.delete("/remove_me.txt").error is None
    missing = backend.read("/remove_me.txt")
    print("删除后读取的错误：", missing.error)
    assert missing.error is not None  # 这里报“找不到”恰好证明删除成功。

    print("\n记住：write 整份写，edit 局部改，glob 找名字，grep 找正文。")
    print("练一练：把 offset 改成 0，猜猜第④步会打印什么。同步修改对应断言。")
    print("保留的清单：", folder / "shopping.txt")


if __name__ == "__main__":
    main()
