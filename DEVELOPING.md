# Руководство для разработчиков (Developer Guide)

Данный документ предназначен для разработчиков, которые будут поддерживать или расширять сервер `mactoip`.

---

## 1. Архитектура проекта

Проект спроектирован по модульному принципу на современном асинхронном стеке Python:

- **Web-фреймворк**: [FastAPI](https://fastapi.tiangolo.com/) (валидация на Pydantic v2, автодокументация OpenAPI).
- **ORM и база данных**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) с диалектом SQLite. База сохраняется в `data/devices.db`.
- **Сборщик пакетов и виртуальное окружение**: [uv](https://docs.astral.sh/uv/) (быстрый менеджер зависимостей нового поколения).
- **Тестирование**: [pytest](https://docs.pytest.org/) + `httpx` / FastAPI `TestClient`.

### Структура каталогов
```text
mactoip/
├── pyproject.toml              # Зависимости и метаданные проекта
├── README.md                   # Руководство пользователя
├── DEVELOPING.md               # Руководство разработчика (этот файл)
├── .agents/                    # Инженерные правила и субагенты качества (ECC)
├── data/                       # Локальная база SQLite (игнорируется в Git)
├── examples/
│   └── wirenboard_client/     # Референсные клиентские скрипты для контроллеров
├── src/
│   └── mactoip/
│       ├── __init__.py         # Точка входа в пакет
│       ├── config.py           # Настройки (хост, порт, путь к БД)
│       ├── database.py         # SQLAlchemy engine, SessionLocal, get_db
│       ├── models.py           # Модели таблиц SQLAlchemy (Device)
│       ├── schemas.py          # Pydantic схемы валидации входных/выходных данных
│       ├── crud.py             # Операции с БД (создание, обновление, поиск)
│       ├── utils.py            # Утилиты нормализации MAC-адресов
│       ├── main.py             # Маршруты FastAPI и обработка запросов
│       └── static/
│           └── index.html      # Встроенная веб-панель мониторинга
└── tests/
    ├── test_api.py             # Интеграционные тесты API эндпоинтов
    └── test_utils.py           # Модульные тесты нормализации MAC-адресов
```

---

## 2. Схема базы данных

Таблица `devices`:

| Поле | Тип | Индекс | Описание |
| :--- | :--- | :---: | :--- |
| `id` | Integer (PK) | Да | Автоинкрементный идентификатор записи |
| `mac` | String(17) | Да (Unique) | Нормализованный MAC-адрес вида `AA:BB:CC:DD:EE:FF` |
| `ip` | String(45) | Да | Текущий IPv4 или IPv6 адрес |
| `hostname` | String(255) | Нет | Сетевое имя устройства (опционально) |
| `comment` | String(255) | Нет | Пользовательская локация или комментарий (опционально) |
| `first_seen`| DateTime | Нет | Дата и время первой регистрации устройства в UTC |
| `last_seen` | DateTime | Нет | Дата и время последнего обращения в UTC |
| `update_count` | Integer | Нет | Общее количество обращений/пигов от устройства |

---

## 3. Пошаговый гайд: Как добавить новое поле от контроллера

*Пример: вам потребовалось принимать от Wiren Board серийный номер (`serial_number`) или версию прошивки (`firmware_version`).*

### Шаг 1. Добавьте колонку в SQLAlchemy модель ([src/mactoip/models.py](src/mactoip/models.py))
```python
# models.py
class Device(Base):
    # ... существующие поля ...
    serial_number = Column(String(100), nullable=True)
```

### Шаг 2. Обновите Pydantic схемы ([src/mactoip/schemas.py](src/mactoip/schemas.py))
```python
# schemas.py
class HeartbeatRequest(BaseModel):
    mac: str
    ip: str
    hostname: Optional[str] = None
    serial_number: Optional[str] = None  # <-- Новое входное поле

class DeviceResponse(BaseModel):
    # ... существующие поля ...
    serial_number: Optional[str] = None  # <-- Поле в ответе API
```

### Шаг 3. Обновите логику сохранения в CRUD ([src/mactoip/crud.py](src/mactoip/crud.py))
В функции `upsert_device`:
```python
# При создании нового:
device = Device(
    mac=req.mac,
    ip=req.ip,
    hostname=req.hostname,
    serial_number=req.serial_number,  # <--
    first_seen=now,
    last_seen=now,
    update_count=1,
)

# При обновлении существующего:
if req.serial_number and device.serial_number != req.serial_number:
    device.serial_number = req.serial_number
```

### Шаг 4. Отобразите в веб-панели ([src/mactoip/static/index.html](src/mactoip/static/index.html))
Добавьте колонку `<th>Серийный номер</th>` в таблицу и выведите `<td>${d.serial_number || '—'}</td>`.

### Шаг 5. Напишите тест ([tests/test_api.py](tests/test_api.py))
Добавьте проверку в тестовый набор, чтобы убедиться, что поле корректно сохраняется и отдается в API:
```python
def test_heartbeat_with_serial(client):
    res = client.post("/api/devices/heartbeat", json={
        "mac": "AA:BB:CC:11:22:33",
        "ip": "192.168.1.10",
        "serial_number": "WB-SN-998877"
    })
    assert res.status_code == 200
    assert res.json()["device"]["serial_number"] == "WB-SN-998877"
```

---

## 4. Запуск и разработка

### Установка зависимостей в окружение:
```bash
uv sync --all-groups
```

### Запуск тестов:
```bash
uv run pytest -v
```

### Локальный запуск с горячей перезагрузкой:
```bash
uv run uvicorn mactoip.main:app --host 0.0.0.0 --port 8000 --reload
```
