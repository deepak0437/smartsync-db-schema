# syntax=docker/dockerfile:1
# Not a running service - this image only exists to carry alembic +
# the migration scripts + smartsync_db's models into prod, where a
# one-off `docker run` invokes `alembic upgrade head` per schema.
# config.yaml (DB connection) is bind-mounted in at run time, not baked in.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash"]
