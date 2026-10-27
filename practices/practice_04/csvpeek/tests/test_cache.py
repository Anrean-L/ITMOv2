import sys
import threading
import unittest
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from csvpeek.cache import AnalysisCache


class CacheTests(unittest.TestCase):
    def test_lru_and_oversize(self):
        cache = AnalysisCache(max_entries=2, max_bytes=100)
        calls = []
        def compute(data):
            calls.append(data)
            return {'v': data.decode()}
        for data in (b'a', b'b', b'a', b'c', b'b'):
            cache.get_or_compute(data, compute)
        self.assertEqual(calls, [b'a', b'b', b'c', b'b'])
        small = AnalysisCache(max_bytes=1)
        small.get_or_compute(b'z', compute)
        small.get_or_compute(b'z', compute)
        self.assertEqual(calls.count(b'z'), 2)

    def test_concurrent_single_flight(self):
        cache = AnalysisCache()
        entered, release = threading.Event(), threading.Event()
        calls = []
        def compute(data):
            calls.append(data)
            entered.set()
            self.assertTrue(release.wait(5))
            return {'v': 'ok'}
        with ThreadPoolExecutor(max_workers=20) as pool:
            first = pool.submit(cache.get_or_compute, b'key', compute)
            self.assertTrue(entered.wait(5))
            others = [pool.submit(cache.get_or_compute, b'key', compute) for _ in range(19)]
            release.set()
            results = [first.result()] + [f.result() for f in others]
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(calls, [b'key'])

    def test_failure_is_not_cached(self):
        cache = AnalysisCache()
        calls = []
        def fail(data):
            calls.append(data)
            raise ValueError('invalid')
        for _ in range(2):
            with self.assertRaises(ValueError):
                cache.get_or_compute(b'a', fail)
        self.assertEqual(len(calls), 2)

    def test_byte_limit_eviction_and_key_bytes(self):
        cache = AnalysisCache(max_entries=128, max_bytes=20)
        calls = []
        def compute(data):
            calls.append(data)
            return {'v': 'ab'}
        for data in (b'a', b'b', b'a', b'\xef\xbb\xbfa', b'a\r\n'):
            cache.get_or_compute(data, compute)
        self.assertEqual(calls, [b'a', b'b', b'\xef\xbb\xbfa', b'a\r\n'])
        cache.get_or_compute(b'b', compute)
        self.assertEqual(calls[-1], b'b')

    def test_waiters_receive_failure_and_later_retry_succeeds(self):
        cache = AnalysisCache()
        entered, waiting, release = threading.Event(), threading.Event(), threading.Event()
        original_result = Future.result
        calls = []

        def wait_for_result(future, *args, **kwargs):
            waiting.set()
            return original_result(future, *args, **kwargs)

        def compute(data):
            calls.append(data)
            entered.set()
            self.assertTrue(release.wait(5))
            raise ValueError('bad CSV')

        with ThreadPoolExecutor(max_workers=2) as pool:
            owner = pool.submit(cache.get_or_compute, b'a', compute)
            self.assertTrue(entered.wait(5))
            with patch.object(Future, 'result', wait_for_result):
                waiter = pool.submit(cache.get_or_compute, b'a', compute)
                self.assertTrue(waiting.wait(5))
                release.set()
            for future in (owner, waiter):
                with self.assertRaisesRegex(ValueError, 'bad CSV'):
                    future.result()
        self.assertEqual(calls, [b'a'])
        self.assertEqual(cache.get_or_compute(b'a', lambda _: {'ok': True}), b'{"ok":true}')

    def test_distinct_keys_are_not_blocked(self):
        cache = AnalysisCache()
        entered, release = threading.Event(), threading.Event()
        def slow(_):
            entered.set()
            self.assertTrue(release.wait(5))
            return {'v': 1}
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(cache.get_or_compute, b'first', slow)
            self.assertTrue(entered.wait(5))
            second = pool.submit(cache.get_or_compute, b'second', lambda _: {'v': 2})
            self.assertEqual(second.result(timeout=5), b'{"v":2}')
            release.set()
            self.assertEqual(first.result(timeout=5), b'{"v":1}')

    def test_new_cache_is_empty_and_uses_serialized_byte_length(self):
        cache = AnalysisCache(max_entries=128, max_bytes=10)
        calls = []
        def compute(data):
            calls.append(data)
            return {'v': 'ab'}  # exactly 10 UTF-8 JSON bytes
        self.assertEqual(len(cache.get_or_compute(b'a', compute)), 10)
        cache.get_or_compute(b'a', compute)
        self.assertEqual(calls, [b'a'])
        AnalysisCache(max_entries=128, max_bytes=10).get_or_compute(b'a', compute)
        self.assertEqual(calls, [b'a', b'a'])
