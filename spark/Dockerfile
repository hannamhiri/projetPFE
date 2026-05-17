FROM apache/spark:3.5.2

USER root

# Installer Python et pip
RUN apt-get update && apt-get install -y python3 python3-pip curl

# Installer pyspark et psycopg2
RUN pip install pyspark psycopg2-binary

# Great Expectations + dépendances
RUN pip install great_expectations pandas sqlalchemy

# Télécharger le driver JDBC PostgreSQL
RUN curl -o /opt/spark/jars/postgresql.jar https://jdbc.postgresql.org/download/postgresql-42.7.1.jar

USER root
WORKDIR /opt/jobs
CMD ["tail", "-f", "/dev/null"]
