"""Process-local LRU and single-flight coordination."""

from collections import OrderedDict
from concurrent.futures import Future
import hashlib
import json
from threading import Lock


def serialize(result):
    return json.dumps(result, ensure_ascii=True, separators=(',', ':')).encode('utf-8')


class AnalysisCache:
    def __init__(self, max_entries=128, max_bytes=16 * 1024 * 1024):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries = OrderedDict()
        self._size = 0
        self._pending = {}
        self._lock = Lock()

    def get_or_compute(self, data, compute):
        key = hashlib.sha256(data).digest()
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
            future = self._pending.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._pending[key] = future
        if not owner:
            return future.result()
        try:
            value = serialize(compute(data))
        except BaseException as exc:
            with self._lock:
                self._pending.pop(key)
                future.set_exception(exc)
            raise
        with self._lock:
            if len(value) <= self.max_bytes and self.max_entries > 0:
                self._entries[key] = value
                self._size += len(value)
                while len(self._entries) > self.max_entries or self._size > self.max_bytes:
                    _, old = self._entries.popitem(last=False)
                    self._size -= len(old)
            self._pending.pop(key)
            future.set_result(value)
        return value
