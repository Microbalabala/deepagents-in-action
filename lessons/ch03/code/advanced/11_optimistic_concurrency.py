"""进阶 11：用版本号阻止过期写入。不需要真实数据库服务。
运行：.venv/bin/python lessons/ch03/code/advanced/11_optimistic_concurrency.py
这是 SQLite 原理实验，不代表 Backend 已自动实现版本控制。
"""


def main():
    import sqlite3

    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE files (path TEXT PRIMARY KEY, content TEXT, version INTEGER)")
        db.execute("INSERT INTO files VALUES (?, ?, ?)", ("/report.md", "base", 7))
        # 模拟两个编辑者先后读取同一个版本；之后 A 先提交。
        seen_by_a = db.execute("SELECT version FROM files WHERE path=?", ("/report.md",)).fetchone()[0]
        seen_by_b = db.execute("SELECT version FROM files WHERE path=?", ("/report.md",)).fetchone()[0]

        a = db.execute(
            "UPDATE files SET content=?, version=version+1 WHERE path=? AND version=?",
            ("base + A", "/report.md", seen_by_a),
        )
        # B 还拿着旧版本号，因此 WHERE 条件不再匹配，更新行数为 0。
        b = db.execute(
            "UPDATE files SET content=?, version=version+1 WHERE path=? AND version=?",
            ("base + B", "/report.md", seen_by_b),
        )
        assert a.rowcount == 1
        assert b.rowcount == 0, "过期版本不能覆盖成功更新"
        current = db.execute("SELECT content, version FROM files WHERE path=?", ("/report.md",)).fetchone()
        assert current == ("base + A", 8)
    print("PASS: 过期写入被检测，A 的内容未被 B 覆盖")


if __name__ == "__main__":
    main()
