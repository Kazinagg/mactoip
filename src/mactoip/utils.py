import re

MAC_CLEAN_REGEX = re.compile(r"[^0-9a-fA-F]")

def normalize_mac(raw_mac: str) -> str:
    """
    Нормализует MAC-адрес к стандартному формату XX:XX:XX:XX:XX:XX в верхнем регистре.
    Поддерживает входные форматы:
    - 00:1a:2b:3c:4d:5e
    - 00-1A-2B-3C-4D-5E
    - 001a.2b3c.4d5e
    - 001a2b3c4d5e
    """
    if not raw_mac:
        raise ValueError("MAC-адрес не может быть пустым")

    cleaned = MAC_CLEAN_REGEX.sub("", raw_mac).upper()

    if len(cleaned) != 12:
        raise ValueError(
            f"Некорректная длина MAC-адреса: '{raw_mac}'. Ожидается 12 шестнадцатеричных символов."
        )

    # Разбиваем на пары по 2 символа: AA:BB:CC:DD:EE:FF
    return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))
