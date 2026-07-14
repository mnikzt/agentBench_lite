import ipaddress
import socket
from urllib.parse import urlparse


def validate_public_http_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Only http and https URLs are allowed"
    if not parsed.hostname:
        return "URL host is required"
    try:
        addresses = socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return f"Could not resolve host: {exc}"
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return "Private, loopback, link-local, and multicast hosts are not allowed"
    return None
