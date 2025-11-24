import argparse
import ipaddress
import socket
from typing import Dict, List, Optional, Tuple

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

SOCKET_TIMEOUT = 1.0
RECV_BYTES = 512


def read_ip_file(path: str) -> List[str]:
    ips: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                ipaddress.ip_address(line)
            except ValueError:
                raise ValueError(f"Invalid IP address in input file: {line}") from None
            ips.append(line)
    return ips


def probe_port(ip: str, port: int, payload: Optional[bytes] = None) -> Tuple[bool, str]:
    description = ""
    try:
        with socket.create_connection((ip, port), timeout=SOCKET_TIMEOUT) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
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


def http_probe(ip: str, port: int) -> Tuple[bool, str]:
    request = f"HEAD / HTTP/1.0\r\nHost: {ip}\r\n\r\n".encode()
    return probe_port(ip, port, payload=request)


def scan_host(ip: str) -> Dict[str, object]:
    host_name = resolve_hostname(ip)
    open_ports: Dict[int, str] = {}
    for port in SCAN_PORTS:
        if port in (80, 8080):
            is_open, desc = http_probe(ip, port)
        elif port in (443, 8443):
            payload = b"\x16" + b"\x03\x00" + b"\x00\x79"
            is_open, desc = probe_port(ip, port, payload=payload)
        else:
            is_open, desc = probe_port(ip, port)
        if is_open:
            open_ports[port] = desc
    classification = classify_host(open_ports)
    return {
        "ip": ip,
        "host_name": host_name,
        "open_ports": sorted(open_ports.keys()),
        "details": open_ports,
        "classification": classification,
    }


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


def resolve_hostname(ip: str) -> Optional[str]:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return None


def format_table(rows: List[Dict[str, object]]) -> str:
    headers = ("IP Address", "Host Name", "Classification", "Open Ports", "Details")
    formatted_rows = []
    for row in rows:
        ports = ", ".join(str(port) for port in row["open_ports"]) or "None"
        details = "; ".join(
            f"{port}: {row['details'][port]}" if row["details"][port] else f"{port}: (open)"
            for port in row["open_ports"]
        ) or ""
        formatted_rows.append(
            (
                row["ip"],
                row["host_name"] or "",
                row["classification"],
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan network endpoints from a file and classify them.")
    parser.add_argument("input_file", help="Path to a text file containing IP addresses (one per line).")
    parser.add_argument(
        "--timeout",
        type=float,
        default=SOCKET_TIMEOUT,
        help="Socket timeout per port probe (seconds).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global SOCKET_TIMEOUT
    SOCKET_TIMEOUT = max(0.2, args.timeout)
    ips = read_ip_file(args.input_file)
    results = [scan_host(ip) for ip in ips]
    print(format_table(results))


if __name__ == "__main__":
    main()
