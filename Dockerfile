FROM python:3.13.1

LABEL maintainer="vitas_khr@@yahoo.com"
LABEL org.opencontainers.image.title="routeAPI"
LABEL org.opencontainers.image.description="Builder for routeAPI "
LABEL org.opencontainers.image.url=""
LABEL org.opencontainers.image.source=""
LABEL org.opencontainers.image.vendor=""
LABEL org.opencontainers.image.authors=""


WORKDIR /app
RUN mkdir -p /app/tmp
ENV PROMETHEUS_MULTIPROC_DIR=/app/tmp
ENV PG_TIMEZONE="America/New_York"
ENV REDIS_URL="redis://redis:6379"
ENV BILLING_LOGGER_INTERVAL=180

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8180

CMD ["python","main.py"]
