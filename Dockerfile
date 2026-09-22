FROM python:3.12-slim
WORKDIR /app
COPY aquasentinel aquasentinel
COPY web web
COPY config config
COPY data data
RUN useradd --uid 10001 --create-home app && mkdir runtime && chown app runtime
USER app
EXPOSE 8765
CMD ["python", "-m", "aquasentinel.server", "--host", "0.0.0.0", "--read-only", "--demo", "--usgs-fixture", "--weather-dir", "data/weather"]
