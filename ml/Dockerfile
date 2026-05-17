FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --timeout=300 -r requirements.txt
COPY . .

ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV PYTHONUNBUFFERED=1

# ← Jupyter au lieu de train.py directement
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", \
     "--no-browser", "--allow-root", \
     "--NotebookApp.token=''"]