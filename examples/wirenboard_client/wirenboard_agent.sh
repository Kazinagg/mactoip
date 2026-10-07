#!/usr/bin/env bash
# ==============================================================================
# Wiren Board Heartbeat Agent (Bash / curl)
# Референсный скрипт для контроллеров Wiren Board (WB 6 / WB 7 / WB 8)
# Отправляет MAC и текущий IP адрес контроллера на центральный сервер mactoip
# ==============================================================================

set -euo pipefail

# --- Конфигурация ---
# Адрес центрального сервера реестра (замените на IP вашего сервера в сети)
REGISTRY_SERVER="${REGISTRY_SERVER:-http://192.168.1.100:8000}"

# Сетевой интерфейс по умолчанию. Если пустой, скрипт определит основной автоматически
INTERFACE="${INTERFACE:-}"

# Автоматическое определение основного сетевого интерфейса (с маршрутом по умолчанию)
if [ -z "$INTERFACE" ]; then
    INTERFACE=$(ip route show default 2>/dev/null | awk '{print $5}' | head -n1 || true)
fi

# Если не удалось определить маршрут по умолчанию, проверяем eth0, eth1 или wlan0
if [ -z "$INTERFACE" ] || [ ! -d "/sys/class/net/$INTERFACE" ]; then
    for candidate in eth0 eth1 wlan0 enp0s3; do
        if [ -d "/sys/class/net/$candidate" ]; then
            INTERFACE="$candidate"
            break
        fi
    done
fi

if [ -z "$INTERFACE" ]; then
    echo "[ERROR] Не удалось определить активный сетевой интерфейс!" >&2
    exit 1
fi

# Получаем MAC-адрес интерфейса
MAC=$(cat "/sys/class/net/$INTERFACE/address" 2>/dev/null || ip link show "$INTERFACE" | awk '/ether/ {print $2}')
MAC=$(echo "$MAC" | tr '[:lower:]' '[:upper:]')

# Получаем текущий IPv4 адрес интерфейса
IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1 || true)

if [ -z "$IP" ]; then
    echo "[WARN] Интерфейс $INTERFACE не имеет назначенного IPv4 адреса." >&2
    exit 0
fi

HOSTNAME=$(hostname -s 2>/dev/null || cat /etc/hostname || echo "wirenboard")

# Формируем JSON
JSON_PAYLOAD=$(cat <<EOF
{
  "mac": "$MAC",
  "ip": "$IP",
  "hostname": "$HOSTNAME"
}
EOF
)

# Отправляем на сервер реестра
echo "[INFO] Отправка данных на $REGISTRY_SERVER/api/devices/heartbeat (MAC: $MAC, IP: $IP, Host: $HOSTNAME)..."
RESPONSE=$(curl -s -S --max-time 10 -X POST "$REGISTRY_SERVER/api/devices/heartbeat" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD")

echo "[INFO] Ответ сервера: $RESPONSE"
