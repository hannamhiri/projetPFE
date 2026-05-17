FROM apache/superset:latest
USER root
RUN apt-get update && \
    apt-get install -y pkg-config default-libmysqlclient-dev build-essential libpq-dev && \
    /app/.venv/bin/python -m ensurepip && \
    /app/.venv/bin/python -m pip install mysqlclient PyMySQL clickhouse-connect psycopg2-binary
USER superset