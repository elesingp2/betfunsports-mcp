FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir . && \
    playwright install --with-deps chromium

ENTRYPOINT ["bfs-mcp"]
