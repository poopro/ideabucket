import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from bot import capture_server


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(url: str, token: str = "", origin: str = ""):
    headers = {}
    if token:
        headers["X-Ideabucket-Token"] = token
    if origin:
        headers["Origin"] = origin
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers))


def test_api_requires_token_and_rejects_web_origins(isolated_app: Path) -> None:
    token = "test-token-that-is-long-enough-123456"
    port = free_port()
    server = capture_server.start_server(port, lambda _url: True)
    url = f"http://127.0.0.1:{port}/api/data"
    try:
        try:
            request(url)
            raise AssertionError("missing token should fail")
        except urllib.error.HTTPError as error:
            assert error.code == 401

        try:
            request(url, token, "https://attacker.example")
            raise AssertionError("web origin should fail")
        except urllib.error.HTTPError as error:
            assert error.code == 403
            assert error.headers.get("Access-Control-Allow-Origin") is None

        with request(url, token) as response:
            payload = json.load(response)
            assert response.status == 200
            assert payload["items"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_capture_reports_queued_or_uninitialized(isolated_app: Path) -> None:
    token = "test-token-that-is-long-enough-123456"
    for accepted, expected in ((True, 202), (False, 409)):
        port = free_port()
        server = capture_server.start_server(port, lambda _url, value=accepted: value)
        body = json.dumps({"url": "https://example.com"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/capture",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Ideabucket-Token": token,
            },
        )
        try:
            try:
                response = urllib.request.urlopen(req)
                assert response.status == expected
            except urllib.error.HTTPError as error:
                assert error.code == expected
        finally:
            server.shutdown()
            server.server_close()

