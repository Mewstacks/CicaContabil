FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir Pillow==12.3.0

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --chown=app:app src/apps/intelligence/multimodal.py /app/multimodal.py
USER 10001:10001
EXPOSE 8081
CMD ["python", "multimodal.py"]
