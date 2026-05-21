FROM python:3.11-slim

WORKDIR /app

COPY setup.py requirements.txt ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["requester"]
