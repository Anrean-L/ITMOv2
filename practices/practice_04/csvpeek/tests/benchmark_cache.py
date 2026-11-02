"""Manual benchmark: PYTHONPATH=src python tests/benchmark_cache.py."""

import hashlib
import http.client
import platform
from statistics import mean, median
import threading
from time import perf_counter

from csvpeek.cache import serialize
from csvpeek.server import Server


class NoCache:
    def get_or_compute(self, data, compute):
        hashlib.sha256(data).digest()
        return serialize(compute(data))


def run(server, body):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    times = []
    try:
        for _ in range(20):
            start = perf_counter()
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
            conn.request('POST', '/api/analysis', body, {
                'Content-Type': 'multipart/form-data; boundary=bench',
                'X-Csvpeek-Request': '1'})
            response = conn.getresponse()
            response.read()
            if response.status != 200:
                raise RuntimeError(f'Benchmark request failed: {response.status}')
            conn.close()
            times.append(perf_counter() - start)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    return times


def main():
    data = b'a,b,c\n' + b'abcdefgh,ijklmnop,qrstuvwx\n' * 40000
    body = (b'--bench\r\nContent-Disposition: form-data; name="file"; filename="data.csv"\r\n'
            b'\r\n' + data + b'\r\n--bench--\r\n')
    warm, cold = [], []
    for _ in range(5):
        warm.append(mean(run(Server(0), body)[1:]))
        cold.append(mean(run(Server(0, cache=NoCache()), body)))
    warm_median, cold_median = median(warm), median(cold)
    print(f'Python {platform.python_version()}, {platform.platform()}')
    print(f'File: {len(data)} bytes, 40000 records, SHA-256 {hashlib.sha256(data).hexdigest()}')
    print(f'Median mean response: warm={warm_median:.6f}s, uncached={cold_median:.6f}s')
    print(f'Relative change: {(warm_median / cold_median - 1) * 100:.2f}%')


if __name__ == '__main__':
    main()
