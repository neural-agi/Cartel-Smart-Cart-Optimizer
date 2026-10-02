FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements/base.txt /tmp/cartel-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/cartel-requirements.txt
RUN playwright install --with-deps chromium

COPY backend/app /app/backend/app
COPY backend/alembic.ini /app/backend/alembic.ini

CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
