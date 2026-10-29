#!/usr/bin/env python3
# Copyright (c) 2026 Dustin Liang
# SPDX-License-Identifier: MIT
"""Thin Streamable HTTP proxy for the official Lava MCP endpoint.

This process does not implement Lava tools or stock-data APIs. It forwards
MCP JSON-RPC (Streamable HTTP) to the upstream URL and attaches
``Authorization: Bearer <LAVA_API_KEY>``. Production data still comes from
https://lava.ai-dolphin.com.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.parse
from http.client import HTTPConnection, HTTPException, HTTPSConnection, HTTPResponse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_UPSTREAM = "https://lava.ai-dolphin.com/subscribe/v1/mcp"
MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
MAX_BODY_BYTES = 2 * 1024 * 1024
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Headers copied onto the upstream request. Authorization is set separately.
_REQUEST_HEADERS = (
    "accept",
    "content-type",
    "mcp-protocol-version",
    "mcp-session-id",
    "last-event-id",
)

# Headers copied back to the client. Hop-by-hop and length headers are not.
_RESPONSE_HEADERS = frozenset(
    {
        "content-type",
        "cache-control",
        "mcp-session-id",
        "mcp-protocol-version",
        "www-authenticate",
        "x-request-id",
        "allow",
        "access-control-allow-origin",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-expose-headers",
        "access-control-max-age",
        "vary",
    }
)


class Settings:
    """Process-wide proxy settings. Read on each request so tests can retarget."""

    upstream: str = DEFAULT_UPSTREAM
    timeout: float | None = 180.0


settings = Settings()


def api_key() -> str:
    """Return the configured key, or empty when it is missing or unsafe to send."""
    raw = os.environ.get("LAVA_API_KEY", "").strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw or any(char in raw for char in "\r\n\x00"):
        return ""
    return raw


def _is_loopback_name(hostname: str) -> bool:
    return hostname.lower().rstrip(".") in LOOPBACK_HOSTS


def _hostname_from_host_header(value: str) -> str:
    text = value.strip()
    if text.startswith("["):
        end = text.find("]")
        return text[1:end] if end != -1 else text
    if text.count(":") == 1:
        return text.split(":", 1)[0]
    return text


def _upstream_target(upstream: str) -> tuple[str, str, int | None, str]:
    parts = urllib.parse.urlsplit(upstream)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("LAVA_MCP_UPSTREAM must be an absolute http(s) URL")
    if parts.username or parts.password:
        raise ValueError("put the API key in LAVA_API_KEY, not in the upstream URL")
    path = parts.path or "/"
    target = path if not parts.query else f"{path}?{parts.query}"
    return parts.scheme, parts.hostname, parts.port, target


def _jsonrpc_id(body: bytes) -> object:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict) and "method" in payload and "id" in payload:
        return payload["id"]
    return None


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "lava-mcp-proxy/1.0"

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._handle()

    def setup(self) -> None:
        super().setup()
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

    def _handle(self) -> None:
        if not self._allow_local_client():
            return
        path = urllib.parse.urlsplit(self.path).path
        if path == HEALTH_PATH:
            if self.command != "GET":
                self._error(405, None, "GET /health only")
                return
            self._health()
            return
        if path != MCP_PATH:
            self._error(404, None, "MCP endpoint is /mcp")
            return

        body = self._read_body()
        if body is None:
            return
        # OPTIONS is a browser preflight and does not carry the API key.
        auth = self._authorization()
        if self.command != "OPTIONS" and not auth:
            self._error(
                401,
                _jsonrpc_id(body),
                "LAVA_API_KEY is not set. Export it before starting the proxy, "
                "or send an Authorization header.",
                code=-32001,
            )
            return
        self._forward(body, auth)

    def _allow_local_client(self) -> bool:
        host = self.headers.get("Host")
        if not host or not _is_loopback_name(_hostname_from_host_header(host)):
            self._error(403, None, "local proxy only accepts Host localhost or 127.0.0.1")
            return False
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        parsed = urllib.parse.urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            self._error(403, None, "rejected Origin")
            return False
        if not _is_loopback_name(parsed.hostname):
            self._error(403, None, "rejected Origin; browser clients must be on localhost")
            return False
        return True

    def _read_body(self) -> bytes | None:
        if self.headers.get("Transfer-Encoding"):
            self._error(400, None, "send Content-Length; chunked request bodies are not accepted")
            return None
        if self.command in {"GET", "OPTIONS"}:
            return b""
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            if self.command == "DELETE":
                return b""
            self._error(400, None, "POST requires Content-Length")
            return None
        try:
            length = int(raw_length)
        except ValueError:
            self._error(400, None, "invalid Content-Length")
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(413, None, "request body is too large")
            return None
        return self.rfile.read(length)

    def _authorization(self) -> str | None:
        key = api_key()
        if key:
            return f"Bearer {key}"
        client = (self.headers.get("Authorization") or "").strip()
        if client and not any(char in client for char in "\r\n\x00"):
            return client
        return None

    def _health(self) -> None:
        payload = {
            "ok": True,
            "role": "streamable-http-proxy",
            "mcp_endpoint": MCP_PATH,
            "upstream": settings.upstream,
            "api_key_configured": bool(api_key()),
        }
        self._send_json(200, payload)

    def _forward(self, body: bytes, auth: str | None) -> None:
        try:
            scheme, host, port, target = _upstream_target(settings.upstream)
        except ValueError as exc:
            self._error(500, _jsonrpc_id(body), str(exc))
            return

        headers = self._upstream_headers(auth, len(body))
        connection: HTTPConnection | None = None
        started = False
        try:
            if scheme == "https":
                connection = HTTPSConnection(host, port or 443, timeout=settings.timeout)
            else:
                connection = HTTPConnection(host, port or 80, timeout=settings.timeout)
            outbound = body if self.command in {"POST", "DELETE"} else None
            connection.request(self.command, target, body=outbound, headers=headers)
            upstream = connection.getresponse()
            started = True
            self._relay(upstream)
        except (OSError, HTTPException, TimeoutError) as exc:
            if not started:
                self._error(
                    502,
                    _jsonrpc_id(body),
                    f"upstream request failed: {exc.__class__.__name__}",
                )
        finally:
            if connection is not None:
                connection.close()

    def _upstream_headers(self, auth: str | None, length: int) -> dict[str, str]:
        headers: dict[str, str] = {}
        for name in _REQUEST_HEADERS:
            value = self.headers.get(name)
            if value and not any(char in value for char in "\r\n\x00"):
                headers[name] = value
        if "accept" not in headers:
            headers["accept"] = "application/json, text/event-stream"
        if auth:
            headers["Authorization"] = auth
        if self.command in {"POST", "DELETE"}:
            headers["Content-Length"] = str(length)
        return headers

    def _relay(self, upstream: HTTPResponse) -> None:
        reason = upstream.reason or "OK"
        try:
            reason.encode("latin-1")
        except UnicodeEncodeError:
            reason = "OK"
        self.send_response(upstream.status, reason)
        for key, value in upstream.getheaders():
            if key.lower() in _RESPONSE_HEADERS and not any(char in value for char in "\r\n\x00"):
                self.send_header(key, value)
        no_body = upstream.status in {204, 304} or self.command == "HEAD"
        known_length = upstream.length is not None
        # Chunked framing is HTTP/1.1. Older clients get a raw body and a close.
        use_chunked = not no_body and not known_length and self.request_version >= "HTTP/1.1"
        if no_body:
            self.send_header("Content-Length", "0")
        elif use_chunked:
            self.send_header("Transfer-Encoding", "chunked")
        elif known_length:
            self.send_header("Content-Length", str(upstream.length))
        else:
            self.close_connection = True
        self.end_headers()
        if no_body:
            return
        try:
            if known_length:
                remaining = upstream.length or 0
                while remaining > 0:
                    chunk = upstream.read1(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    self.wfile.write(chunk)
                    self.wfile.flush()
                return
            while True:
                chunk = upstream.read1(65536)
                if not chunk:
                    break
                if use_chunked:
                    self.wfile.write(b"%X\r\n" % len(chunk))
                    self.wfile.write(chunk)
                    self.wfile.write(b"\r\n")
                else:
                    self.wfile.write(chunk)
                self.wfile.flush()
            if use_chunked:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _error(self, status: int, request_id: object, message: str, code: int = -32000) -> None:
        self._send_json(
            status,
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
        )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s [%s] %s\n" % (self.log_date_time_string(), self.address_string(), fmt % args))


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ProxyHandler)
    server.daemon_threads = True
    return server


def _bind_host_allowed(host: str) -> bool:
    if _is_loopback_name(host):
        return True
    return os.environ.get("LAVA_PROXY_ALLOW_REMOTE", "").strip() == "1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Forward Streamable HTTP MCP traffic to the official Lava endpoint. "
            "Does not implement Lava APIs."
        )
    )
    parser.add_argument("--host", default=os.environ.get("LAVA_PROXY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("LAVA_PROXY_PORT", "8787")))
    parser.add_argument("--upstream", default=os.environ.get("LAVA_MCP_UPSTREAM", DEFAULT_UPSTREAM))
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("LAVA_PROXY_TIMEOUT", "180")),
        help="upstream timeout in seconds; 0 waits without a limit",
    )
    args = parser.parse_args(argv)
    if not _bind_host_allowed(args.host):
        print(
            "refusing to bind %s (set LAVA_PROXY_ALLOW_REMOTE=1 to listen beyond loopback)" % args.host,
            file=sys.stderr,
        )
        return 2
    if args.port < 0 or args.port > 65535:
        print("port must be 0..65535", file=sys.stderr)
        return 2
    if args.timeout < 0:
        print("timeout must be >= 0", file=sys.stderr)
        return 2

    settings.upstream = args.upstream
    settings.timeout = None if args.timeout == 0 else args.timeout
    try:
        httpd = create_server(args.host, args.port)
    except OSError as exc:
        print("failed to bind %s:%s: %s" % (args.host, args.port, exc), file=sys.stderr)
        return 1

    bound_host, bound_port = httpd.server_address[:2]
    display_host = "127.0.0.1" if bound_host in {"0.0.0.0", "::"} else bound_host
    print("lava-mcp proxy listening on http://%s:%s/mcp" % (display_host, bound_port), flush=True)
    print("upstream %s" % settings.upstream, flush=True)
    print("auth Authorization: Bearer <LAVA_API_KEY>", flush=True)
    if not api_key():
        print("warning: LAVA_API_KEY is not set; /mcp requests will fail until it is", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping", flush=True)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
