import asyncio

from app.tools.url_safety import validate_public_http_url, validate_public_response_peer


class _PeerSocket:
    def __init__(self, ip: str) -> None:
        self.ip = ip

    def getpeername(self):
        return (self.ip, 443)


class _NetworkStream:
    def __init__(self, ip: str) -> None:
        self.ip = ip

    def get_extra_info(self, key: str):
        if key == "socket":
            return _PeerSocket(self.ip)
        return None


class _Response:
    def __init__(self, ip: str) -> None:
        self.extensions = {"network_stream": _NetworkStream(ip)}


def test_validate_public_http_url_rejects_loopback_host():
    error = asyncio.run(validate_public_http_url("http://127.0.0.1:8000"))

    assert error == "Private, loopback, link-local, and multicast hosts are not allowed"


def test_validate_public_response_peer_rejects_private_peer():
    error = validate_public_response_peer(_Response("10.0.0.2"))

    assert error == "Remote peer resolved to a private or local address"


def test_validate_public_response_peer_accepts_public_peer():
    error = validate_public_response_peer(_Response("8.8.8.8"))

    assert error is None
