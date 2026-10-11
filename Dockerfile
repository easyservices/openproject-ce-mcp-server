FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --extra budget-comparison --no-editable

FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app \
    && install -d --owner=app --group=app /app/logs

COPY --from=build --chown=app:app /app/.venv /app/.venv

USER app

EXPOSE 8000

ENTRYPOINT ["openproject-ce-mcp-server"]
