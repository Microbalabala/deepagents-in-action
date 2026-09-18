"""进阶 10：给后端加一个记录操作的外壳。无需模型和 API Key。
运行：.venv/bin/python lessons/ch03/code/advanced/10_audit_backend.py
先完成主线 01–06；本例仅记录审计，不实现授权。
"""
from tempfile import TemporaryDirectory
from deepagents.backends import FilesystemBackend

import hashlib
import time
import asyncio
from deepagents.backends.protocol import BackendProtocol


class AuditedBackend(BackendProtocol):
    def __init__(self, inner):
        self.inner = inner
        self.events = []

    # 统一在一次真实存储操作前后记录耗时和结果，不记录文件正文。
    def _run(self, operation, path, fn):
        started = time.perf_counter()
        event = {
            "operation": operation,
            "path_hash": hashlib.sha256(str(path).encode()).hexdigest(),
        }
        try:
            result = fn()
            results = result if isinstance(result, list) else [result]
            event["ok"] = all(getattr(item, "error", None) is None for item in results)
            return result
        except Exception as exc:
            event["ok"] = False
            event["exception_type"] = type(exc).__name__
            raise
        finally:
            event["elapsed_ms"] = (time.perf_counter() - started) * 1000
            self.events.append(event)

    def ls(self, path):
        return self._run("ls", path, lambda: self.inner.ls(path))

    def read(self, file_path, offset=0, limit=2000):
        return self._run("read", file_path, lambda: self.inner.read(file_path, offset=offset, limit=limit))

    def write(self, file_path, content):
        return self._run("write", file_path, lambda: self.inner.write(file_path, content))

    def edit(self, file_path, old_string, new_string, replace_all=False):
        return self._run("edit", file_path, lambda: self.inner.edit(file_path, old_string, new_string, replace_all))

    def delete(self, file_path):
        return self._run("delete", file_path, lambda: self.inner.delete(file_path))

    def glob(self, pattern, path=None):
        return self._run("glob", path, lambda: self.inner.glob(pattern, path))

    def grep(self, pattern, path=None, glob=None, *, max_count=None):
        return self._run("grep", path, lambda: self.inner.grep(pattern, path, glob, max_count=max_count))

    def upload_files(self, files):
        return self._run("upload_files", [p for p, _ in files], lambda: self.inner.upload_files(files))

    def download_files(self, paths):
        return self._run("download_files", paths, lambda: self.inner.download_files(paths))


def main():
    with TemporaryDirectory(prefix="ch03-audit-") as directory:
        # 外层只增加记录能力，实际文件仍由里面的 FilesystemBackend 保存。
        backend = AuditedBackend(FilesystemBackend(root_dir=directory, virtual_mode=True))
        assert backend.write("/a.txt", "hello").error is None
        assert backend.read("/a.txt").file_data["content"] == "hello"
        assert backend.delete("/a.txt").error is None
        assert backend.read("/a.txt").error is not None

        # 独立 py 文件直接用 asyncio.run，不需要额外线程处理事件循环。
        async def async_read_and_write():
            assert (await backend.awrite("/async.txt", "async-ok")).error is None
            assert (await backend.aread("/async.txt")).file_data["content"] == "async-ok"
        asyncio.run(async_read_and_write())

        for event in backend.events:
            print(event["operation"], "成功" if event["ok"] else "失败", round(event["elapsed_ms"], 3), "ms")
        assert len(backend.events) == 6
        print("记住：包装器增加审计，里面的 Backend 仍负责存储。")


if __name__ == "__main__":
    main()
