FROM bitnami/python:3.11-debian-11

WORKDIR /app

RUN install_packages \
    libjpeg-dev \
    libpng-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6

RUN pip install poetry==1.5.1 --no-cache
RUN poetry config virtualenvs.create false

COPY [ "poetry.toml", "poetry.lock", "pyproject.toml", "./" ]

# We don't want the tests
COPY src/bot ./src/bot

RUN poetry install --only main

ARG build
ENV BUILD_SHA=$build

ENTRYPOINT [ "python", "-m", "bot" ]
