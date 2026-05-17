FROM python:3.11-slim
RUN apt-get update && apt-get install -y git
RUN pip install dbt-clickhouse==1.8.0

WORKDIR /dbt
CMD ["tail", "-f", "/dev/null"]