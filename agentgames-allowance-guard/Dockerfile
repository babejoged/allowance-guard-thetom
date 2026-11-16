FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home guard
WORKDIR /app
COPY server.py guard.py deploy.py nginx.conf ./
COPY web ./web
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
USER guard
EXPOSE 10000
CMD ["python", "deploy.py"]
