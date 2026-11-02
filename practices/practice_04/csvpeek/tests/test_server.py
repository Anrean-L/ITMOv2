import http.client
import json
import sys
import threading
import unittest
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from csvpeek.server import Server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, body=b'a,b\n,2\n', headers=None):
        boundary = b'csvpeek-test'
        data = (b'--' + boundary + b'\r\nContent-Disposition: form-data; name="file"; filename="x.csv"\r\n'
                b'Content-Type: text/csv\r\n\r\n' + body + b'\r\n--' + boundary + b'--\r\n')
        values = {'Content-Type': 'multipart/form-data; boundary=csvpeek-test',
                  'X-Csvpeek-Request': '1'}
        if headers is not None:
            values.update(headers)
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('POST', '/api/analysis', data, values)
        response = conn.getresponse()
        contents = response.read()
        conn.close()
        return response.status, contents

    def test_analysis_and_cache(self):
        with patch('csvpeek.server.analyze', wraps=__import__('csvpeek.analysis', fromlist=['analyze']).analyze) as fn:
            a, first = self.request(b'x,x\n,1\n')
            b, second = self.request(b'x,x\n,1\n')
        self.assertEqual((a, b), (200, 200))
        self.assertEqual(first, second)
        self.assertEqual(fn.call_count, 1)
        self.assertEqual(json.loads(first)['columns'][1]['missing_count'], 0)

    def test_rejected_before_analysis(self):
        for headers in ({'X-Csvpeek-Request': '0'}, {'Origin': 'null'},
                        {'Origin': 'http://evil.example'}, {'Host': 'evil.example'}):
            with self.subTest(headers=headers), patch('csvpeek.server.analyze') as fn, \
                    patch.object(self.server.cache, 'get_or_compute') as cache:
                status, _ = self.request(headers=headers)
                self.assertEqual(status, 403)
                fn.assert_not_called()
                cache.assert_not_called()

    def test_cache_response_identical_after_eviction(self):
        from csvpeek.analysis import analyze
        from csvpeek.cache import AnalysisCache
        with patch.object(self.server, 'cache', AnalysisCache(max_entries=1)), \
                patch('csvpeek.server.analyze', wraps=analyze) as fn:
            first = self.request(b'eviction\n1\n')
            hit = self.request(b'eviction\n1\n')
            self.request(b'other\n2\n')
            after = self.request(b'eviction\n1\n')
            self.assertEqual(first, hit)
            self.assertEqual(first, after)
            self.assertEqual(fn.call_count, 3)

    def test_filename_and_mime_do_not_change_result_or_cache_key(self):
        from csvpeek.analysis import analyze
        from csvpeek.cache import AnalysisCache
        with patch.object(self.server, 'cache', AnalysisCache()), \
                patch('csvpeek.server.analyze', wraps=analyze) as fn:
            outputs = []
            for filename, mime in [('a.csv', 'text/csv'), ('b.dat', 'application/octet-stream')]:
                body = (f'--b\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                        f'Content-Type: {mime}\r\n\r\n'.encode() + b'x\n1\n\r\n--b--\r\n')
                conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
                conn.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                             'X-Csvpeek-Request': '1'})
                response = conn.getresponse()
                self.assertEqual(response.getheader('Content-Type'), 'application/json; charset=utf-8')
                outputs.append((response.status, response.read()))
                conn.close()
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(fn.call_count, 1)

    def test_error_and_repeat(self):
        for _ in range(2):
            status, data = self.request(b'a,b\n1\n')
            self.assertEqual(status, 422)
            error = json.loads(data)['error']
            self.assertEqual(error['code'], 'invalid_structure')
            self.assertEqual(error['details']['record'], 2)

    def test_internal_error_is_safe_and_retryable(self):
        with patch('csvpeek.server.analyze', side_effect=RuntimeError('secret internal detail')):
            status, body = self.request(b'internal_error_test\nvalue\n')
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body)['error']['code'], 'internal_error')
        self.assertNotIn(b'secret internal detail', body)
        status, _ = self.request(b'internal_error_test\nvalue\n')
        self.assertEqual(status, 200)

    def test_disconnected_waiter_does_not_cancel_shared_analysis(self):
        from csvpeek.analysis import analyze
        entered, waiting, release = threading.Event(), threading.Event(), threading.Event()
        original_result = Future.result
        data = b'disconnect_test\nvalue\n'
        body = (b'--b\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
                b'\r\n' + data + b'\r\n--b--\r\n')
        def slow(value):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('timed out')
            return analyze(value)
        def wait_for_result(future, *args, **kwargs):
            waiting.set()
            return original_result(future, *args, **kwargs)
        with patch('csvpeek.server.analyze', side_effect=slow) as compute, \
                patch.object(Future, 'result', wait_for_result):
            owner = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            owner.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                          'X-Csvpeek-Request': '1'})
            self.assertTrue(entered.wait(5))
            waiter = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            waiter.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                           'X-Csvpeek-Request': '1'})
            self.assertTrue(waiting.wait(5))
            waiter.close()
            release.set()
            response = owner.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), analyze(data))
            owner.close()
            self.assertEqual(compute.call_count, 1)

    def test_disconnected_owner_can_finish_and_populate_cache(self):
        from csvpeek.analysis import analyze
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        data = b'abandoned_request\nvalue\n'
        body = (b'--b\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
                b'\r\n' + data + b'\r\n--b--\r\n')
        original = self.server.cache.get_or_compute
        def track(*args):
            try:
                return original(*args)
            finally:
                finished.set()
        def slow(value):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('timed out')
            return analyze(value)
        with patch('csvpeek.server.analyze', side_effect=slow) as compute, \
                patch.object(self.server.cache, 'get_or_compute', side_effect=track):
            conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            conn.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                         'X-Csvpeek-Request': '1'})
            self.assertTrue(entered.wait(5))
            conn.close()
            release.set()
            self.assertTrue(finished.wait(5))
            status, result = self.request(data)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(result), analyze(data))
            self.assertEqual(compute.call_count, 1)

    def test_aborted_upload_is_not_cached(self):
        import socket
        with patch.object(self.server.cache, 'get_or_compute') as cache:
            with socket.create_connection(('127.0.0.1', self.port), timeout=5) as sock:
                sock.sendall(f'POST /api/analysis HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n'
                             'X-Csvpeek-Request: 1\r\nContent-Type: multipart/form-data; boundary=b\r\n'
                             'Content-Length: 100\r\n\r\npartial'.encode())
                sock.shutdown(socket.SHUT_WR)
                self.assertIn(b' 400 ', sock.recv(1024).split(b'\r\n')[0])
            cache.assert_not_called()

    def test_cors_preflight(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('OPTIONS', '/api/analysis', headers={'Origin': 'http://evil.example',
                     'Access-Control-Request-Method': 'POST',
                     'Access-Control-Request-Headers': 'x-csvpeek-request'})
        result = conn.getresponse()
        self.assertEqual(result.status, 403)
        self.assertIsNone(result.getheader('Access-Control-Allow-Origin'))
        result.read()
        conn.close()

    def test_same_origin_and_wrong_field(self):
        status, _ = self.request(headers={'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual(status, 200)
        status, body = self.request(b'a\n\xff')
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)['error']['code'], 'invalid_encoding')

    def test_twenty_different_files(self):
        from csvpeek.analysis import analyze
        def fetch(i):
            return self.request(f'col{i}\n{i}\n'.encode())
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(fetch, range(20)))
        for i, (status, raw) in enumerate(results):
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), analyze(f'col{i}\n{i}\n'.encode()))

    def test_file_size_boundary(self):
        from csvpeek.analysis import FILE_LIMIT
        data = b'a\n' + (b'x' * 104855 + b'\n') * 100
        data += b'x' * (FILE_LIMIT - len(data))
        self.assertEqual(len(data), FILE_LIMIT)
        status, _ = self.request(data)
        self.assertEqual(status, 200)
        status, response = self.request(data + b'x')
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(response)['error']['details']['kind'], 'file_bytes')
        # A maximum-size CSV plus more than 1 MiB of MIME framing is valid.
        multipart = (b'--b\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
                     b'\r\n' + data + b'\r\n--b--\r\n' + b'x' * (1024 * 1024 + 1))
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        conn.request('POST', '/api/analysis', multipart, {
            'Content-Type': 'multipart/form-data; boundary=b', 'X-Csvpeek-Request': '1'})
        response = conn.getresponse()
        self.assertEqual(response.status, 200, response.read())
        conn.close()

    def test_structural_limit_details(self):
        cases = [(b','.join([b'x'] * 1001), 'columns', 1000, 'columns'),
                 (b'x\n' + b'a\n' * 100001, 'rows', 100000, 'rows'),
                 (b'x\n' + b'a' * 131073, 'field_bytes', 131072, 'bytes')]
        for value, kind, limit, unit in cases:
            with self.subTest(kind=kind):
                status, body = self.request(value)
                self.assertEqual(status, 413)
                self.assertEqual(json.loads(body)['error']['details'],
                                 {'kind': kind, 'limit': limit, 'unit': unit})

    def test_loopback_and_example(self):
        self.assertEqual(self.server.server_address, ('127.0.0.1', self.port))
        data = (Path(__file__).resolve().parents[1] / 'examples' / 'people.csv').read_bytes()
        status, body = self.request(data)
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual((result['row_count'], result['column_count']), (4, 3))
        self.assertEqual([item['missing_count'] for item in result['columns']], [0, 1, 0])

    def test_large_multipart_framing_is_not_file_size(self):
        # The file is tiny; a legal MIME epilogue must not count towards its size.
        data = (b'--b\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
                b'\r\na\n1\n\r\n--b--\r\n' + b'x' * (1024 * 1024 + 1))
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        conn.request('POST', '/api/analysis', data, {
            'Content-Type': 'multipart/form-data; boundary=b', 'X-Csvpeek-Request': '1'})
        response = conn.getresponse()
        self.assertEqual(response.status, 200, response.read())
        conn.close()

    def test_total_request_bound_is_not_reported_as_file_limit(self):
        from csvpeek.server import REQUEST_LIMIT
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.putrequest('POST', '/api/analysis')
        conn.putheader('Content-Type', 'multipart/form-data; boundary=b')
        conn.putheader('X-Csvpeek-Request', '1')
        conn.putheader('Content-Length', str(REQUEST_LIMIT + 1))
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.read())['error']['code'], 'invalid_request')
        conn.close()

    def test_unsupported_method_and_security(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('GET', '/api/analysis')
        self.assertEqual(conn.getresponse().status, 405)
        conn.close()
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('TRACE', '/', headers={'Origin': 'null'})
        self.assertEqual(conn.getresponse().status, 403)
        conn.close()

    def test_binary_file_and_multipart_errors(self):
        for data, code in [(b'', 'empty_csv'), (b'\xef\xbb\xbfa\n', None),
                           (b'a\n"unterminated', 'invalid_structure')]:
            status, response = self.request(data)
            self.assertEqual(status, 200 if code is None else 422)
            if code:
                self.assertEqual(json.loads(response)['error']['code'], code)
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('POST', '/api/analysis', b'bad',
                     {'Content-Type': 'text/plain', 'X-Csvpeek-Request': '1'})
        response = conn.getresponse()
        self.assertEqual(response.status, 415)
        response.read()
        conn.close()

    def test_bad_multipart_never_returns_file_content(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('POST', '/api/analysis', b'private data', {
            'Content-Type': 'multipart/form-data; boundary=b', 'X-Csvpeek-Request': '1'})
        response = conn.getresponse()
        body = response.read()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(body)['error']['code'], 'invalid_request')
        self.assertNotIn(b'private data', body)
        conn.close()

    def test_non_ascii_multipart_header_is_invalid_request(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('POST', '/api/analysis', b'bad', {
            'Content-Type': 'multipart/form-data; boundary=é', 'X-Csvpeek-Request': '1'})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.read())['error']['code'], 'invalid_request')
        conn.close()

    def test_multipart_missing_extra_and_exact_bytes(self):
        header = b'Content-Disposition: form-data; name="file"; filename="a.csv"\r\n\r\n'
        data = b'name,note\r\n"A","first\r\nsecond"\r\n'
        bodies = [b'--b--\r\n', b'--b\r\n' + header + data +
                  b'\r\n--b\r\n' + header + data + b'\r\n--b--\r\n',
                  b'--b\r\n' + header + data]  # missing closing delimiter
        for body in bodies:
            conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            conn.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                         'X-Csvpeek-Request': '1'})
            response = conn.getresponse()
            self.assertEqual(response.status, 400)
            response.read()
            conn.close()
        body = b'--b\r\n' + header + data + b'\r\n--b--\r\n'
        with patch.object(self.server.cache, 'get_or_compute', return_value=b'{}') as cache:
            conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            conn.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                         'X-Csvpeek-Request': '1'})
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            response.read()
            self.assertEqual(cache.call_args.args[0], data)
            conn.close()

    def test_security_port_80_without_binding_privileged_port(self):
        from csvpeek.server import Handler
        from email.message import Message
        from types import SimpleNamespace
        handler = object.__new__(Handler)
        handler.server = SimpleNamespace(server_port=80)
        handler.command = 'POST'
        handler.path = '/api/analysis'
        handler.headers = Message()
        handler.headers['Host'] = '127.0.0.1'
        handler.headers['Origin'] = 'http://127.0.0.1'
        handler.headers['X-Csvpeek-Request'] = '1'
        self.assertTrue(handler._safe())

    def test_missing_or_duplicate_host(self):
        import socket
        for host in (b'', b'Host: invalid\r\n',
                     f'Host: 127.0.0.1:{self.port}\r\nHost: 127.0.0.1:{self.port}\r\n'.encode()):
            with self.subTest(host=host), socket.create_connection(('127.0.0.1', self.port)) as sock:
                sock.sendall(b'GET / HTTP/1.1\r\n' + host + b'Connection: close\r\n\r\n')
                self.assertIn(b' 403 ', sock.recv(1024).split(b'\r\n')[0])

    def test_security_header_matrix(self):
        import socket
        host = f'Host: 127.0.0.1:{self.port}\r\n'.encode()
        cases = [
            (host + b'Origin: null\r\n', 403),
            (host + b'Origin: http://127.0.0.1:1\r\n', 403),
            (host + b'Origin: https://127.0.0.1:1\r\n', 403),
            (host + b'Origin: http://a\r\nOrigin: http://b\r\n', 403),
            (host, 403),
            (host + b'X-Csvpeek-Request: 1\r\nX-Csvpeek-Request: 1\r\n', 403),
            (host + b'x-csvpeek-request: 1\r\n', 415),
            (host + b'X-Forwarded-Host: evil.example\r\nX-Csvpeek-Request: 1\r\n', 415),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers), socket.create_connection(('127.0.0.1', self.port)) as sock:
                sock.sendall(b'POST /api/analysis HTTP/1.1\r\n' + headers +
                             b'Content-Length: 0\r\nConnection: close\r\n\r\n')
                self.assertEqual(int(sock.recv(1024).split(b' ')[1]), expected)

    def test_expect_security_precedes_continue(self):
        import socket
        with socket.create_connection(('127.0.0.1', self.port)) as sock:
            sock.sendall(f'POST /api/analysis HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n'
                         'Expect: 100-continue\r\nContent-Length: 999\r\n\r\n'.encode())
            self.assertIn(b' 403 ', sock.recv(1024).split(b'\r\n')[0])

    def test_invalid_http_framing(self):
        import socket
        host = f'Host: 127.0.0.1:{self.port}\r\n'.encode()
        for framing in (b'Content-Length: 0\r\nContent-Length: 0\r\n',
                        b'Content-Length: nope\r\n',
                        b'Content-Length: 0\r\nTransfer-Encoding: chunked\r\n'):
            with self.subTest(framing=framing), socket.create_connection(('127.0.0.1', self.port)) as sock:
                sock.sendall(b'POST /api/analysis HTTP/1.1\r\n' + host +
                             b'X-Csvpeek-Request: 1\r\nContent-Type: multipart/form-data; boundary=b\r\n' +
                             framing + b'Connection: close\r\n\r\n')
                self.assertIn(b' 400 ', sock.recv(1024).split(b'\r\n')[0])
