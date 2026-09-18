"""实验 04：Store 是柜子，namespace 是柜子里的抽屉。

运行：.venv/bin/python lessons/ch03/code/04_store.py
观察三个条件：同柜同抽屉、同柜不同抽屉、新柜同名抽屉。
"""

from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore


def alice_namespace(runtime):
    # namespace 必须由函数返回一个元组。单元素元组的逗号不能省略。
    # 本实验是固定身份，不需要读取 runtime；生产环境应从可信身份生成 namespace。
    return ("alice",)


def bob_namespace(runtime):
    return ("bob",)


def main():
    # Store 是实际保存数据的容器；StoreBackend 给它套上文件读写接口。
    store = InMemoryStore()
    alice = StoreBackend(store=store, namespace=alice_namespace)

    print("\n① Alice 将偏好放进自己的抽屉")
    assert alice.write("/preference.txt", "请使用中文回答。").error is None

    print("\n② 新 Backend 对象 + 原 Store + 同一 namespace")
    another_alice = StoreBackend(store=store, namespace=alice_namespace)
    shared = another_alice.read("/preference.txt")
    assert shared.error is None, shared.error
    print("能读到：", shared.file_data["content"])

    print("\n③ 原 Store + Bob 的 namespace + 完全相同的文件名")
    bob = StoreBackend(store=store, namespace=bob_namespace)
    isolated = bob.read("/preference.txt")
    assert isolated.error is not None
    print("读不到：", isolated.error)

    print("\n④ 新 InMemoryStore + Alice 的 namespace")
    empty_store = InMemoryStore()
    new_alice = StoreBackend(store=empty_store, namespace=alice_namespace)
    missing = new_alice.read("/preference.txt")
    assert missing.error is not None
    print("还是读不到：换了一个空柜子，抽屉名字相同也没有用。")

    print("\n记住：共享文件需要同一份 Store 数据和相同 namespace。")
    print("InMemoryStore 在内存中，不会因为名字里有 Store 就抗进程重启。")
    print("本实验是直接调用存储层，不涉及线程；跨线程访问同一 namespace 也遵循此规则。")
    print("练一练：让 bob 使用 alice_namespace，观察隔离是否还存在。同步调整断言。")


if __name__ == "__main__":
    main()
