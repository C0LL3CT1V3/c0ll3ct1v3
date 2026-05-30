# bookworm + apt sandbox workaround (see Dockerfile.worker)
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN printf 'APT::Sandbox::User "root";\n' > /etc/apt/apt.conf.d/99docker-apt \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
