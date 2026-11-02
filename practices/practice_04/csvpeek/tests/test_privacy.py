import contextlib
import http.client
import io
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from csvpeek.server import Server


class PrivacyTests(unittest.TestCase):
    def test_requests_do_not_use_temporary_files_or_log_user_data(self):
        server = Server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        captured = io.StringIO()
        def request(data):
            body = (b'--b\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
                    b'\r\n' + data + b'\r\n--b--\r\n')
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            conn.request('POST', '/api/analysis', body, {'Content-Type': 'multipart/form-data; boundary=b',
                         'X-Csvpeek-Request': '1'})
            response = conn.getresponse()
            status, result = response.status, response.read()
            conn.close()
            return status, result
        try:
            with contextlib.redirect_stderr(captured), \
                    patch('tempfile.TemporaryFile', side_effect=AssertionError('temporary file')), \
                    patch('tempfile.NamedTemporaryFile', side_effect=AssertionError('temporary file')):
                status, body = request(b'private_header\nsecret_value\n')
                self.assertEqual(status, 200)
                status, body = request(b'private_header\n"broken')
                self.assertEqual(status, 422)
                self.assertNotIn(b'private_header', body)
                self.assertNotIn(b'broken', body)
            self.assertNotIn('private_header', captured.getvalue())
            self.assertNotIn('secret_value', captured.getvalue())
            self.assertNotIn('Traceback', captured.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
