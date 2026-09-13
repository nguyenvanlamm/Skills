FROM python:3.12-slim

WORKDIR /app

# libpq-dev + gcc: build psycopg2 if a wheel is unavailable.
# postgresql-client: provides pg_isready, which entrypoint.sh uses to wait for the DB.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
