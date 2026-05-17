# dagster/Dockerfile
FROM python:3.11-slim

WORKDIR /dagster

# Dépendances système
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation Dagster + intégration dbt
RUN pip install \
    dagster==1.7.* \
    dagster-webserver==1.7.* \
    dagster-postgres==0.23.* \
    dagster-dbt==0.23.* \
    dbt-clickhouse==1.7.* \
    dbt-core==1.7.* \
    docker

# Copie du code Dagster
COPY . /dagster/

EXPOSE 3000