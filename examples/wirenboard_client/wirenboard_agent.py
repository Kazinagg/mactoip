#!/usr/bin/env python3
"""
Wiren Board Heartbeat Agent (Python 3, без внешних зависимостей)
Референсный клиентский скрипт для запуска на контроллерах Wiren Board.
Может запускаться как однократно (через cron), так и в режиме фонового демона (--daemon).
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def get_default_interface() -> str:
    """Определяет сетевой интерфейс по умолчанию через таблицу маршрутизации."""
    try:
        out = subprocess.check_output(["ip", "route", "show", "default"], text=True)
        tokens = out.strip().split()
        if "dev" in tokens:
            idx = tokens.index("dev")
            return tokens[idx + 1]
    except Exception:
        pass

    for iface in ["eth0", "eth1", "wlan0", "enp0s3"]:
        if os.path.exists(f"/sys/class/net/{iface}"):
            return iface
    return ""


def get_mac_address(interface: str) -> str:
    """Считывает MAC-адрес интерфейса."""
    sys_path = f"/sys/class/net/{interface}/address"
    if os.path.exists(sys_path):
        with open(sys_path, "r", encoding="utf-8") as f:
            return f.read().strip().upper()

    try:
        out = subprocess.check_output(["ip", "link", "show", interface], text=True)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("link/ether"):
                return line.split()[1].upper()
    except Exception:
        pass
    return ""


def get_ip_address(interface: str) -> str:
    """Получает IPv4 адрес интерфейса."""
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", interface], text=True)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return ""


def send_heartbeat(server_url: str, mac: str, ip: str, hostname: str, timeout: int = 10) -> bool:
    endpoint = server_url.rstrip("/") + "/api/devices/heartbeat"
    payload = json.dumps({
        "mac": mac,
        "ip": ip,
        "hostname": hostname,
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            print(f"[OK] Ответ сервера ({resp.status}): {data}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Ошибка сервера {e.code}: {e.read().decode('utf-8', errors='ignore')}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Сбой подключения к {endpoint}: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiren Board Heartbeat Client")
    parser.add_argument(
        "--server",
        default=os.getenv("REGISTRY_SERVER", "http://192.168.1.100:8000"),
        help="URL сервера реестра (default: http://192.168.1.100:8000)",
    )
    parser.add_argument(
        "--interface",
        default=os.getenv("INTERFACE", ""),
        help="Сетевой интерфейс (eth0, eth1, wlan0). Если не указан, определяется автоматически.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Работать в режиме демона (периодический опрос в цикле)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Интервал отправки в секундах для режима --daemon (default: 60)",
    )

    args = parser.parse_args()

    iface = args.interface or get_default_interface()
    if not iface:
        print("[ERROR] Не удалось определить сетевой интерфейс", file=sys.stderr)
        sys.exit(1)

    hostname = socket.gethostname()

    while True:
        mac = get_mac_address(iface)
        ip = get_ip_address(iface)

        if not mac or not ip:
            print(f"[WARN] Не удалось получить MAC или IP для интерфейса '{iface}'", file=sys.stderr)
        else:
            print(f"[INFO] Интерфейс: {iface} | MAC: {mac} | IP: {ip} | Hostname: {hostname}")
            send_heartbeat(args.server, mac, ip, hostname)

        if not args.daemon:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
