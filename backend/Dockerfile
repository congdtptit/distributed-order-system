# One image for every Python container of docker-compose.yml: the four services (seven
# containers), the one-shot init jobs and the tools container used for tests and checks.
# docker-compose.yml mounts ./backend over /app, so a code change needs no rebuild; a change to
# a pyproject.toml or uv.lock does: docker compose build.
FROM python:3.12.13-slim-bookworm

RUN pip install --no-cache-dir --disable-pip-version-check uv==0.13.6

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY . .
RUN uv sync --frozen

CMD ["python", "-m", "common.service"]
