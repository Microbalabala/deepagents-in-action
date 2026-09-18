"""实验 05：Composite 是分拣员，不是新的存储介质。

运行：.venv/bin/python lessons/ch03/code/05_composite.py
/memories/ 开头的文件交给 Store；其余交给磁盘。
"""

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langgraph.store.memory import InMemoryStore


def main():
    folder = Path(__file__).resolve().parent / "output" / "05_composite"
    folder.mkdir(parents=True, exist_ok=True)
    disk = FilesystemBackend(root_dir=folder, virtual_mode=True)
    store = InMemoryStore()
    memory = StoreBackend(store=store, namespace=lambda runtime: ("alice",))

    # default：没有命中任何路由时交给谁。
    # routes：命中指定前缀时交给谁。这里故意只配置一个前缀。
    router = CompositeBackend(default=disk, routes={"/memories/": memory})

    print("\n① 写 /draft.txt：不匹配 /memories/，进入磁盘")
    assert router.write("/draft.txt", "这是正在编辑的草稿。").error is None
    disk_file = folder / "draft.txt"
    assert disk_file.is_file()
    print("找到真实文件：", disk_file)

    print("\n② 写 /memories/preference.txt：匹配前缀，进入 Store")
    assert router.write("/memories/preference.txt", "Alice 喜欢中文。").error is None
    assert not (folder / "memories" / "preference.txt").exists()
    print("磁盘里没有 memories/preference.txt。")

    print("\n③ 外部统一通过 router 读取，不需要关心目标后端")
    for path in ("/draft.txt", "/memories/preference.txt"):
        result = router.read(path)
        assert result.error is None, result.error
        print(path, "→", result.file_data["content"])

    print("\n④ 看看 Store 内部收到的路径")
    # 路由转交文件时会去掉 /memories 前缀。
    # 外部 /memories/preference.txt → Store 内部 /preference.txt。
    internal = memory.read("/preference.txt")
    assert internal.error is None, internal.error
    print("Store 中 /preference.txt：", internal.file_data["content"])

    print("\n记住：Composite 只负责按路径分发，文件仍由具体 Backend 保存。")
    print("本例 Store 是内存版；路由不会把它自动变成持久化数据库。")
    print("练一练：把路由改成 /profiles/，并把对应读写路径一起修改。")


if __name__ == "__main__":
    main()
