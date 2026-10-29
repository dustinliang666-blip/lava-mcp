# Copyright (c) 2026 Dustin Liang
# SPDX-License-Identifier: MIT
"""Local tests for the thin MCP proxy. No network and no third-party packages."""

from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proxy import server  # noqa: E402


class UpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._record(b"")
        self._reply(405, b'{"jsonrpc":"2.0","id":null,"error":{"code":-32000,"message":"POST only"}}')

    def do_POST(self) -> None:  # noqa: N802
        body = self._read()
        self._record(body)
        if self.path.split("?", 1)[0].endswith("/sse"):
            self._sse()
            return
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        status = int(query.get("status", ["200"])[0])
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"forwarded": True, "bytes": len(body)},
            }
        ).encode()
        if status != 200:
            payload = b'{"jsonrpc":"2.0","id":1,"error":{"code":-32001,"message":"invalid key"}}'
        self._reply(status, payload)

    def do_DELETE(self) -> None:  # noqa: N802
        self._record(b"")
        self._reply(202, b"")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._record(b"")
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b"data: first\n\n")
        self.wfile.flush()
        self.server.first_byte.set()
        if not self.server.release.wait(5):
            return
        self.wfile.write(b"data: second\n\n")
        self.wfile.flush()
        self.close_connection = True

    def _read(self) -> bytes:
        length = int(self.headers.get("Content-Length") or "0")
        return self.rfile.read(length)

    def _record(self, body: bytes) -> None:
        self.server.hits += 1
        self.server.last = {
            "method": self.command,
            "path": self.path,
            "body": body,
            "authorization": self.headers.get("Authorization"),
            "accept": self.headers.get("Accept"),
            "content_type": self.headers.get("Content-Type"),
            "session": self.headers.get("Mcp-Session-Id"),
            "protocol": self.headers.get("MCP-Protocol-Version"),
        }

    def _reply(self, status: int, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", "sess-1")
        self.send_header("WWW-Authenticate", 'Bearer realm="lava-test"')
        self.send_header("X-Request-Id", "req-test")
        if payload:
            self.send_header("Content-Length", str(len(payload)))
        else:
            self.send_header("Content-Length", "0")
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        return


class StreamUpstreamHandler(UpstreamHandler):
    """HTTP/1.0 so the body can be flushed before the handler finishes."""

    protocol_version = "HTTP/1.0"


class ProxyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._old_key = os.environ.get("LAVA_API_KEY")
        os.environ["LAVA_API_KEY"] = "test-key"
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        self.upstream.daemon_threads = True
        self.upstream.hits = 0
        self.upstream.last = None
        self.upstream.first_byte = threading.Event()
        self.upstream.release = threading.Event()
        self.upstream_thread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upstream_thread.start()
        upstream_port = self.upstream.server_address[1]
        server.settings.upstream = "http://127.0.0.1:%s/subscribe/v1/mcp" % upstream_port
        server.settings.timeout = 5
        self.proxy = server.create_server("127.0.0.1", 0)
        self.proxy_thread = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        self.proxy_thread.start()
        self.port = self.proxy.server_address[1]

    def tearDown(self) -> None:
        self.upstream.release.set()
        self.proxy.shutdown()
        self.proxy.server_close()
        self.upstream.shutdown()
        self.upstream.server_close()
        if self._old_key is None:
            os.environ.pop("LAVA_API_KEY", None)
        else:
            os.environ["LAVA_API_KEY"] = self._old_key
        server.settings.upstream = server.DEFAULT_UPSTREAM
        server.settings.timeout = 180

    def request(
        self,
        method: str = "POST",
        path: str = "/mcp",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        data = body if method in {"POST", "DELETE"} else None
        req = urllib.request.Request(
            "http://127.0.0.1:%s%s" % (self.port, path),
            data=data,
            method=method,
            headers=headers or {},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, dict(response.headers.items()), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()

    def test_forwards_jsonrpc_and_injects_bearer_from_env(self) -> None:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "get_stock_news_heat",
                "params": {"stock_name": "宁德时代"},
            }
        ).encode()
        status, headers, body = self.request(
            body=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18",
                "Mcp-Session-Id": "client-session",
                "Authorization": "Bearer client-should-not-win",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["result"]["forwarded"], True)
        self.assertEqual(headers["Mcp-Session-Id"], "sess-1")
        self.assertEqual(headers["X-Request-Id"], "req-test")
        recorded = self.upstream.last
        self.assertEqual(recorded["path"], "/subscribe/v1/mcp")
        self.assertEqual(recorded["authorization"], "Bearer test-key")
        self.assertEqual(recorded["body"], payload)
        self.assertEqual(recorded["accept"], "application/json, text/event-stream")
        self.assertEqual(recorded["content_type"], "application/json")
        self.assertEqual(recorded["session"], "client-session")
        self.assertEqual(recorded["protocol"], "2025-06-18")

    def test_passes_upstream_error_status_and_www_authenticate(self) -> None:
        port = self.upstream.server_address[1]
        server.settings.upstream = "http://127.0.0.1:%s/subscribe/v1/mcp?status=401" % port
        status, headers, body = self.request(
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertIn("lava-test", headers["WWW-Authenticate"])
        self.assertEqual(json.loads(body)["error"]["message"], "invalid key")

    def test_missing_key_does_not_call_upstream(self) -> None:
        os.environ.pop("LAVA_API_KEY", None)
        status, _, body = self.request(
            body=b'{"jsonrpc":"2.0","id":4,"method":"initialize","params":{}}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        parsed = json.loads(body)
        self.assertEqual(parsed["id"], 4)
        self.assertIn("LAVA_API_KEY", parsed["error"]["message"])
        self.assertEqual(self.upstream.hits, 0)

    def test_client_authorization_used_when_env_is_unset(self) -> None:
        os.environ.pop("LAVA_API_KEY", None)
        status, _, _ = self.request(
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize"}',
            headers={"Content-Type": "application/json", "Authorization": "Bearer from-client"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.upstream.last["authorization"], "Bearer from-client")

    def test_health_does_not_call_upstream(self) -> None:
        status, _, body = self.request(method="GET", path="/health")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["role"], "streamable-http-proxy")
        self.assertTrue(payload["api_key_configured"])
        self.assertEqual(self.upstream.hits, 0)

    def test_rejects_non_loopback_origin_before_upstream(self) -> None:
        status, _, body = self.request(
            body=b"{}",
            headers={"Content-Type": "application/json", "Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertIn("Origin", json.loads(body)["error"]["message"])
        self.assertEqual(self.upstream.hits, 0)

    def test_allows_localhost_origin(self) -> None:
        status, _, _ = self.request(
            body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
            headers={"Content-Type": "application/json", "Origin": "http://localhost:6274"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.upstream.hits, 1)

    def test_rejects_non_loopback_host(self) -> None:
        raw = (
            b"POST /mcp HTTP/1.1\r\n"
            b"Host: evil.example\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 2\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            b"{}"
        )
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall(raw)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
        self.assertTrue(data.startswith(b"HTTP/1.1 403"))
        self.assertEqual(self.upstream.hits, 0)

    def test_unknown_path_is_not_proxied(self) -> None:
        status, _, _ = self.request(method="GET", path="/subscribe/v1/secret")
        self.assertEqual(status, 404)
        self.assertEqual(self.upstream.hits, 0)

    def test_get_is_forwarded(self) -> None:
        status, _, body = self.request(method="GET", path="/mcp", headers={"Accept": "text/event-stream"})
        self.assertEqual(status, 405)
        self.assertIn(b"POST only", body)
        self.assertEqual(self.upstream.last["method"], "GET")
        self.assertEqual(self.upstream.last["path"], "/subscribe/v1/mcp")

    def test_options_preflight_does_not_require_a_key(self) -> None:
        os.environ.pop("LAVA_API_KEY", None)
        status, headers, _ = self.request(
            method="OPTIONS",
            path="/mcp",
            headers={"Origin": "http://127.0.0.1:8787", "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(status, 204)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])

    def test_upstream_down_returns_jsonrpc_502(self) -> None:
        server.settings.upstream = "http://127.0.0.1:9/subscribe/v1/mcp"
        server.settings.timeout = 2
        status, _, body = self.request(
            body=b'{"jsonrpc":"2.0","id":9,"method":"initialize"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 502)
        parsed = json.loads(body)
        self.assertEqual(parsed["id"], 9)
        self.assertIn("upstream", parsed["error"]["message"])

    def test_newline_in_api_key_is_not_sent(self) -> None:
        os.environ["LAVA_API_KEY"] = "good\r\nX-Injected: yes"
        status, _, _ = self.request(
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.upstream.hits, 0)


class StreamingProxyTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["LAVA_API_KEY"] = "test-key"
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), StreamUpstreamHandler)
        self.upstream.daemon_threads = True
        self.upstream.hits = 0
        self.upstream.last = None
        self.upstream.first_byte = threading.Event()
        self.upstream.release = threading.Event()
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        port = self.upstream.server_address[1]
        server.settings.upstream = "http://127.0.0.1:%s/subscribe/v1/mcp/sse" % port
        server.settings.timeout = None
        self.proxy = server.create_server("127.0.0.1", 0)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.port = self.proxy.server_address[1]

    def tearDown(self) -> None:
        self.upstream.release.set()
        self.proxy.shutdown()
        self.proxy.server_close()
        self.upstream.shutdown()
        self.upstream.server_close()
        os.environ.pop("LAVA_API_KEY", None)
        server.settings.upstream = server.DEFAULT_UPSTREAM
        server.settings.timeout = 180

    def test_sse_first_chunk_is_forwarded_before_upstream_finishes(self) -> None:
        seen: list[bytes] = []
        done = threading.Event()
        errors: list[BaseException] = []

        def client() -> None:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                conn.request(
                    "POST",
                    "/mcp",
                    body=b'{"jsonrpc":"2.0","id":1,"method":"tools/call"}',
                    headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                )
                response = conn.getresponse()
                while True:
                    chunk = response.read1(64)
                    if not chunk:
                        break
                    seen.append(chunk)
                    if b"first" in b"".join(seen) and not self.upstream.release.is_set():
                        done.set()
                    if b"second" in b"".join(seen):
                        break
                conn.close()
            except BaseException as exc:  # noqa: BLE001 - surface the client failure in the assertion
                errors.append(exc)
                done.set()

        worker = threading.Thread(target=client, daemon=True)
        worker.start()
        self.assertTrue(self.upstream.first_byte.wait(3), "upstream did not start the stream")
        self.assertTrue(done.wait(3), "proxy buffered the SSE body instead of streaming it")
        self.assertFalse(errors, errors)
        self.upstream.release.set()
        worker.join(5)
        self.assertFalse(errors, errors)
        self.assertIn(b"first", b"".join(seen))
        self.assertIn(b"second", b"".join(seen))


class BindGuardTest(unittest.TestCase):
    def test_refuses_non_loopback_without_opt_in(self) -> None:
        old = os.environ.pop("LAVA_PROXY_ALLOW_REMOTE", None)
        try:
            code = server.main(["--host", "0.0.0.0", "--port", "0"])
        finally:
            if old is not None:
                os.environ["LAVA_PROXY_ALLOW_REMOTE"] = old
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
