FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    libpng-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && apt-get clean

RUN pip install poetry==1.3.1 --no-cache
RUN poetry config virtualenvs.create false

COPY [ "poetry.toml", "poetry.lock", "pyproject.toml", "./" ]

# We don't want the tests
COPY src/bot ./src/bot

RUN poetry install --no-dev

ARG build
ENV BUILD_SHA=$build

ENTRYPOINT [ "python", "-m", "bot" ]
