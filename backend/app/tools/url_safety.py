import asyncio
import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse


def _is_disallowed_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return True
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast


async def validate_public_http_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Only http and https URLs are allowed"
    if not parsed.hostname:
        return "URL host is required"
    try:
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return f"Could not resolve host: {exc}"
    for address in addresses:
        if _is_disallowed_ip(address[4][0]):
            return "Private, loopback, link-local, and multicast hosts are not allowed"
    return None


def validate_public_response_peer(response: Any) -> str | None:
    network_stream = response.extensions.get("network_stream")
    if network_stream is None or not hasattr(network_stream, "get_extra_info"):
        return "Could not validate remote peer address"
    socket_obj = network_stream.get_extra_info("socket")
    if socket_obj is None or not hasattr(socket_obj, "getpeername"):
        return "Could not validate remote peer address"
    peername = socket_obj.getpeername()
    if not peername:
        return "Could not validate remote peer address"
    peer_ip = peername[0]
    if _is_disallowed_ip(peer_ip):
        return "Remote peer resolved to a private or local address"
    return None
