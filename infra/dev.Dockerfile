# Development tools for the Python services: Python 3.12 and uv.
# The repository is mounted at /workspace; nothing is copied into the image.
# The virtual environment lives in /opt/venv (a named volume), so the Linux
# packages never mix with the macOS checkout.
FROM python:3.12.13-slim-bookworm

RUN pip install --no-cache-dir --disable-pip-version-check uv==0.13.6

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /workspace
CMD ["sleep", "infinity"]
