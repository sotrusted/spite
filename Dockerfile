FROM python:3.10.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /spite

# Install system dependencies with exact versions
RUN apt-get update && apt-get install -y \
    nginx=1.18.0-6ubuntu14.5 \
    nginx-core=1.18.0-6ubuntu14.5 \
    libnginx-mod-http-geoip2=1.18.0-6ubuntu14.5 \
    libnginx-mod-http-image-filter=1.18.0-6ubuntu14.5 \
    libnginx-mod-http-xslt-filter=1.18.0-6ubuntu14.5 \
    libnginx-mod-mail=1.18.0-6ubuntu14.5 \
    libnginx-mod-stream=1.18.0-6ubuntu14.5 \
    libnginx-mod-stream-geoip2=1.18.0-6ubuntu14.5 \
    memcached=1.6.14-1ubuntu0.1 \
    postgresql-14=14.15-0ubuntu0.22.04.1 \
    postgresql-client-14=14.15-0ubuntu0.22.04.1 \
    redis-server=6:7.4.1-1rl1~jammy1 \
    supervisor=4.2.1-1ubuntu1 \
    python3-dev \
    libpq-dev \
    gcc \
    libmemcached-dev \
    zlib1g-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions
RUN mkdir -p /spite/logs /var/log/supervisor \
    && chown -R www-data:www-data /spite/logs \
    && chown -R www-data:www-data /var/log/supervisor

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install celery==5.4.0

# Copy supervisor configuration
COPY supervisor/spite.conf /etc/supervisor/conf.d/

# Copy gunicorn config
COPY gunicorn_config.py /spite/gunicorn_config.py

# Copy project
COPY . . 