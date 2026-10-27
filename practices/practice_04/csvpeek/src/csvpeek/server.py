"""Local-only HTTP interface; run with python -m csvpeek.server."""

import argparse
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .analysis import AnalysisError, FILE_LIMIT, analyze, limit_error
from .cache import AnalysisCache, serialize

REQUEST_LIMIT = 16 * 1024 * 1024


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128

    def __init__(self, port=8000, cache=None):
        super().__init__(('127.0.0.1', port), Handler)
        self.cache = cache if cache is not None else AnalysisCache()

    def handle_error(self, request, client_address):
        # Request data and tracebacks must not reach the server's logs.
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        pass

    def _safe(self):
        hosts = self.headers.get_all('Host', [])
        port = self.server.server_port
        if len(hosts) != 1 or hosts[0] not in (
                f'127.0.0.1:{port}', *(['127.0.0.1'] if port == 80 else [])):
            return False
        origins = self.headers.get_all('Origin', [])
        if len(origins) > 1:
            return False
        if origins:
            allowed = [f'http://127.0.0.1:{port}']
            if port == 80:
                allowed.append('http://127.0.0.1')
            if origins[0] not in allowed:
                return False
        if self.command == 'POST' and self.path == '/api/analysis':
            if self.headers.get_all('X-Csvpeek-Request', []) != ['1']:
                return False
        return True

    def _send(self, status, body=b'', content_type=None):
        self.send_response(status)
        if content_type:
            self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _reject(self):
        self.close_connection = True
        self._send(403)

    def handle_expect_100(self):
        if not self._safe():
            self._reject()
            return False
        self.send_response_only(100)
        self.end_headers()
        return True

    def _error(self, error):
        self._send(error.status, serialize({'error': {'code': error.code,
                   'message': error.message, 'details': error.details}}),
                   'application/json; charset=utf-8')

    def do_POST(self):
        if not self._safe():
            return self._reject()
        if self.path != '/api/analysis':
            self.close_connection = True
            return self._send(405)
        try:
            data = self._file()
            result = self.server.cache.get_or_compute(data, analyze)
            self._send(200, result, 'application/json; charset=utf-8')
        except AnalysisError as error:
            self.close_connection = True
            self._error(error)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception:
            self.close_connection = True
            self._error(AnalysisError('internal_error', 'Analysis failed', status=500))

    def _file(self):
        invalid = lambda: AnalysisError('invalid_request', 'Invalid multipart request', status=400)
        types = self.headers.get_all('Content-Type', [])
        if len(types) != 1 or self.headers.get_content_type() != 'multipart/form-data':
            raise AnalysisError('unsupported_media_type', 'Expected multipart form data', status=415)
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit() or self.headers.get_all('Transfer-Encoding', []):
            raise invalid()
        digits = lengths[0].lstrip('0') or '0'
        if len(digits) > len(str(REQUEST_LIMIT)):
            raise AnalysisError('invalid_request', 'Multipart request exceeds the request size limit', status=400)
        length = int(digits)
        # This protects memory independently of the CSV file size limit.
        if length > REQUEST_LIMIT:
            raise AnalysisError('invalid_request', 'Multipart request exceeds the request size limit', status=400)
        body = self.rfile.read(length)
        if len(body) != length:
            raise invalid()
        try:
            content_type = types[0].encode('ascii')
        except UnicodeEncodeError as exc:
            raise invalid() from exc
        message = BytesParser(policy=policy.default).parsebytes(
            b'Content-Type: ' + content_type + b'\r\nMIME-Version: 1.0\r\n\r\n' + body)
        if message.defects or not message.is_multipart():
            raise invalid()
        parts = list(message.iter_parts())
        if len(parts) != 1 or parts[0].defects or parts[0].is_multipart():
            raise invalid()
        part = parts[0]
        if (part.get_content_disposition() != 'form-data' or
                part.get_param('name', header='content-disposition') != 'file' or
                part.get_filename() is None or part.get('Content-Transfer-Encoding')):
            raise invalid()
        data = part.get_payload(decode=True)
        if data is None:
            raise invalid()
        if len(data) > FILE_LIMIT:
            raise limit_error('file_bytes', FILE_LIMIT, 'bytes')
        return data

    def do_GET(self):
        if not self._safe():
            return self._reject()
        path = urlsplit(self.path).path
        if path == '/api/analysis':
            return self._send(405)
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/index.html': ('index.html', 'text/html; charset=utf-8'),
                 '/app.css': ('app.css', 'text/css; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if path not in files:
            return self._send(404)
        name, content_type = files[path]
        try:
            content = (Path(__file__).parent / 'web' / name).read_bytes()
        except FileNotFoundError:
            return self._send(404)
        self._send(200, content, content_type)

    do_HEAD = do_GET

    def _other(self):
        if not self._safe():
            return self._reject()
        self.close_connection = True
        self._send(405)

    do_OPTIONS = do_PUT = do_DELETE = do_PATCH = _other

    def __getattr__(self, name):
        if name.startswith('do_'):
            return self._other
        raise AttributeError(name)


def main():
    parser = argparse.ArgumentParser(description='Run the local csvpeek service')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    with Server(args.port) as server:
        print(f'http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
