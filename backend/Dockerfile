FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements/base.txt /tmp/cartel-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/cartel-requirements.txt

COPY backend/app /app/backend/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
