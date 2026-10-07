FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATA_DIR=/app/data

# Копируем манифесты зависимостей для кэширования
COPY pyproject.toml uv.lock README.md ./

# Устанавливаем зависимости без самого проекта
RUN uv sync --frozen --no-dev --no-install-project

# Копируем исходный код приложения
COPY src/ ./src/

# Устанавливаем сам проект
RUN uv sync --frozen --no-dev

# Создаем папку под том базы данных
RUN mkdir -p /app/data

EXPOSE 8000

VOLUME ["/app/data"]

CMD ["uv", "run", "uvicorn", "mactoip.main:app", "--host", "0.0.0.0", "--port", "8000"]
