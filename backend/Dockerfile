FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/app/__init__.py
RUN touch /app/app/__init__.py
RUN touch /app/app/models/__init__.py
RUN touch /app/app/api/__init__.py
RUN touch /app/app/services/__init__.py
RUN touch /app/app/tasks/__init__.py
RUN touch /app/app/core/__init__.py
RUN touch /app/app/ws/__init__.py

EXPOSE 8100

CMD ["sh", "-c", "alembic -c migrations/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8100"]
