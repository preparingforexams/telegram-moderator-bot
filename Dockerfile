FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    libpng-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && apt-get clean

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache

COPY bot bot

ARG build
ENV BUILD_SHA=$build

ENTRYPOINT [ "python", "-m", "bot" ]
