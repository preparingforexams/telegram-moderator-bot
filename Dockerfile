FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache

COPY bot .

ARG build
ENV BUILD_SHA=$build

ENTRYPOINT [ "python", "-m", "bot" ]
