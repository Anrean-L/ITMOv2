"""Exercise the real HTTP transport without an LLM or third-party packages."""

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from service import Shop, make_handler


class HttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = Shop()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.shop))
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()
        cls.shop.close()

    def call(self, method, path, body=None, headers=None):
        headers = {"Content-Type": "application/json", **(headers or {})}
        request = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                          headers=headers, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, response.read().decode()

    def test_login_and_purchase_over_http(self):
        status, _, body = self.call("POST", "/login", {"username": "alice", "password": "learn-alice"})
        self.assertEqual(status, 200)
        token = json.loads(body)["token"]
        status, headers, body = self.call("POST", "/orders", {"product": "chair"}, {"X-Token": token})
        self.assertEqual(status, 201)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(json.loads(body)["price"], 5000)

    def test_health_and_not_found(self):
        status, _, body = self.call("GET", "/health")
        self.assertEqual((status, json.loads(body)), (200, {"status": "ok"}))
        self.assertEqual(self.call("GET", "/missing")[0], 404)

    def test_transport_only_binds_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
