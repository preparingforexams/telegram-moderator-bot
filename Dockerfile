FROM ghcr.io/blindfoldedsurgery/poetry:2.0.1-pipx-3.12-bookworm

USER root

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        libjpeg-dev \
        libpng-dev \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives

USER app

COPY [ "poetry.toml", "poetry.lock", "pyproject.toml", "./" ]

RUN poetry install --no-interaction --ansi --only=main --no-root

# We don't want the tests
COPY src/bot ./src/bot

RUN poetry install --no-interaction --ansi --only-root

ARG APP_VERSION
ENV BUILD_SHA=$APP_VERSION

ENTRYPOINT [ "tini", "--", "poetry", "run", "python", "-m", "bot" ]
