# Примеры клиентских скриптов для Wiren Board

> **Примечание:** Эта папка содержит **референсные примеры** для специалистов и инженеров, настраивающих сами контроллеры Wiren Board. Основной репозиторий посвящен серверу учета и его REST API.

Данные скрипты показывают, как контроллер может автоматически определять свой MAC и текущий локальный IP-адрес и отправлять их на сервер `mactoip`.

---

## 1. Вариант на Bash (`wirenboard_agent.sh`)

Использует стандартные утилиты Linux (`ip`, `curl`, `awk`), которые уже предустановлены на Wiren Board.

### Развертывание на контроллере:
1. Скопируйте файл на контроллер по SSH:
   ```bash
   scp wirenboard_agent.sh root@<IP_КОНТРОЛЛЕРА>:/usr/local/bin/wb-heartbeat.sh
   ssh root@<IP_КОНТРОЛЛЕРА> "chmod +x /usr/local/bin/wb-heartbeat.sh"
   ```

2. Задайте адрес вашего сервера реестра и проверьте вручную:
   ```bash
   REGISTRY_SERVER="http://<IP_СЕРВЕРА>:8000" /usr/local/bin/wb-heartbeat.sh
   ```

3. Настройте запуск по расписанию через `crontab`:
   ```bash
   crontab -e
   ```
   Пример запуска каждые 5 минут (или раз в час / при загрузке):
   ```cron
   # Отправка каждые 5 минут:
   */5 * * * * REGISTRY_SERVER="http://192.168.1.100:8000" /usr/local/bin/wb-heartbeat.sh >/dev/null 2>&1

   # Либо только один раз при загрузке контроллера:
   @reboot sleep 10 && REGISTRY_SERVER="http://192.168.1.100:8000" /usr/local/bin/wb-heartbeat.sh >/dev/null 2>&1
   ```

---

## 2. Вариант на Python 3 (`wirenboard_agent.py`)

Написан исключительно на стандартной библиотеке Python 3 (не требует установки `pip` или внешних пакетов).

### Запуск в режиме службы (Systemd daemon):
Создайте юнит `/etc/systemd/system/wb-heartbeat.service`:
```ini
[Unit]
Description=Wiren Board Heartbeat to MAC-to-IP Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/wirenboard_agent.py --server http://192.168.1.100:8000 --daemon --interval 60
Restart=always
RestartSec=15
User=root

[Install]
WantedBy=multi-user.target
```

Запуск службы:
```bash
systemctl daemon-reload
systemctl enable --now wb-heartbeat.service
```

---

## 3. Использование полученного IP в bash-скриптах и автоматизации

Если на машине администратора или управляющем сервере необходимо быстро подключиться к контроллеру по его MAC-адресу:

```bash
# Получить чистый IP адрес
IP=$(curl -s "http://<IP_СЕРВЕРА>:8000/api/devices/AC:83:F3:12:34:56/ip?format=text")
echo "Контроллер найден по адресу $IP"

# Подключиться по SSH напрямую:
ssh root@$(curl -s "http://<IP_СЕРВЕРА>:8000/api/devices/AC:83:F3:12:34:56/ip?format=text")
```
