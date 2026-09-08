FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/apps/api
COPY apps/api/requirements.lock /app/requirements.lock
RUN uv pip install --system --no-cache --require-hashes -r requirements.lock
COPY alembic.ini /app/alembic.ini
COPY apps/api /app/apps/api
COPY contracts/ai /app/contracts/ai
COPY prompts /app/prompts
CMD ["python", "-m", "uvicorn", "notetaker.main:app", "--host", "0.0.0.0", "--port", "8010", "--no-access-log"]
