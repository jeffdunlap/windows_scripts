import argparse
import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SCAN_PORTS: Tuple[int, ...] = (
    22,   # SSH
    23,   # Telnet
    80,   # HTTP
    443,  # HTTPS
    445,  # SMB
    554,  # RTSP / Cameras
    631,  # IPP printing
    8080, # HTTP alt
    8443, # HTTPS alt
    9100, # JetDirect printing
    3389, # RDP
)

DEFAULT_SOCKET_TIMEOUT = 1.0
RECV_BYTES = 512


@dataclass
class ScanResult:
    ip: str
    host_name: Optional[str]
    open_ports: List[int] = field(default_factory=list)
    details: Dict[int, str] = field(default_factory=dict)
    classification: str = "Unknown"


def read_ip_file(path: str) -> List[str]:
    ips: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                ipaddress.ip_address(line)
            except ValueError as exc:
                raise ValueError(f"Invalid IP address in input file: {line}") from exc
            ips.append(line)
    return ips


def probe_port(ip: str, port: int, timeout: float, payload: Optional[bytes] = None) -> Tuple[bool, str]:
    description = ""
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if payload:
                sock.sendall(payload)
            try:
                received = sock.recv(RECV_BYTES)
                if received:
                    description = received.decode(errors="replace")
            except socket.timeout:
                description = ""
        return True, description.strip()
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False, description


def http_probe(ip: str, port: int, timeout: float) -> Tuple[bool, str]:
    request = f"HEAD / HTTP/1.0\r\nHost: {ip}\r\n\r\n".encode()
    return probe_port(ip, port, timeout=timeout, payload=request)


def resolve_hostname(ip: str) -> Optional[str]:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return None


def classify_host(open_ports: Dict[int, str]) -> str:
    descriptions = " ".join(open_ports.values()).lower()
    ports = set(open_ports)

    if 9100 in ports or "printer" in descriptions or "ipp" in descriptions:
        return "Printer"
    if 3389 in ports or 445 in ports:
        return "Windows server or workstation"
    if 554 in ports or "camera" in descriptions or "rtsp" in descriptions:
        return "Video camera or DVR"
    if 22 in ports:
        if any(keyword in descriptions for keyword in ("ubuntu", "debian", "centos", "linux")):
            return "Linux server"
        if any(keyword in descriptions for keyword in ("router", "switch", "fw")):
            return "Network appliance (SSH)"
        return "SSH-enabled host"
    if 23 in ports:
        return "Network appliance (Telnet)"
    if 80 in ports or 8080 in ports or 443 in ports or 8443 in ports:
        if any(keyword in descriptions for keyword in ("router", "switch", "firewall", "gateway")):
            return "Network appliance (web admin)"
        return "HTTP/HTTPS service detected"
    if 631 in ports:
        return "Printer or print server"
    return "Unknown"


def scan_host(ip: str, timeout: float = DEFAULT_SOCKET_TIMEOUT) -> ScanResult:
    host_name = resolve_hostname(ip)
    open_ports: Dict[int, str] = {}
    for port in SCAN_PORTS:
        if port in (80, 8080):
            is_open, desc = http_probe(ip, port, timeout=timeout)
        elif port in (443, 8443):
            payload = b"\x16" + b"\x03\x00" + b"\x00\x79"
            is_open, desc = probe_port(ip, port, timeout=timeout, payload=payload)
        else:
            is_open, desc = probe_port(ip, port, timeout=timeout)
        if is_open:
            open_ports[port] = desc
    classification = classify_host(open_ports)
    return ScanResult(
        ip=ip,
        host_name=host_name,
        open_ports=sorted(open_ports.keys()),
        details=open_ports,
        classification=classification,
    )


def scan_hosts(ips: Sequence[str], timeout: float = DEFAULT_SOCKET_TIMEOUT) -> List[ScanResult]:
    results: List[ScanResult] = []
    for ip in ips:
        results.append(scan_host(ip, timeout=timeout))
    return results


def format_table(rows: Sequence[ScanResult]) -> str:
    headers = ("IP Address", "Host Name", "Classification", "Open Ports", "Details")
    formatted_rows = []
    for row in rows:
        ports = ", ".join(str(port) for port in row.open_ports) or "None"
        details = "; ".join(
            f"{port}: {row.details[port]}" if row.details[port] else f"{port}: (open)"
            for port in row.open_ports
        ) or ""
        formatted_rows.append(
            (
                row.ip,
                row.host_name or "",
                row.classification,
                ports,
                details,
            )
        )

    column_widths = [len(header) for header in headers]
    for fr in formatted_rows:
        for idx, cell in enumerate(fr):
            column_widths[idx] = max(column_widths[idx], len(cell))

    def render_row(values: Tuple[str, ...]) -> str:
        return " | ".join(value.ljust(column_widths[idx]) for idx, value in enumerate(values))

    separator = "-+-".join("-" * width for width in column_widths)
    lines = [render_row(headers), separator]
    for fr in formatted_rows:
        lines.append(render_row(fr))
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Endpoint Detective - scan and classify network endpoints.")
    parser.add_argument("input_file", help="Path to a text file containing IP addresses (one per line).")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_SOCKET_TIMEOUT,
        help="Socket timeout per port probe (seconds).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    timeout = max(0.2, args.timeout)
    ips = read_ip_file(args.input_file)
    results = scan_hosts(ips, timeout=timeout)
    print(format_table(results))


if __name__ == "__main__":
    main()
