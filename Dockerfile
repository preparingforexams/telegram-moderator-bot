FROM python:3.12-slim-bookworm AS base

RUN groupadd --system --gid 500 app
RUN useradd --system --uid 500 --gid app --create-home --home-dir /app -s /bin/bash app

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        curl \
        libjpeg-dev \
        libpng-dev \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives

# renovate: datasource=pypi depName=poetry
ENV POETRY_VERSION=1.6.1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_IN_PROJECT=false
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 -

USER app
WORKDIR /app

COPY [ "poetry.toml", "poetry.lock", "pyproject.toml", "./" ]

RUN poetry install --no-interaction --ansi --only=main --no-root

FROM base AS prod

# We don't want the tests
COPY src/bot ./src/bot

RUN poetry install --no-interaction --ansi --only-root

ARG APP_VERSION
ENV BUILD_SHA=$APP_VERSION

ENTRYPOINT [ "tini", "--", "poetry", "run", "python", "-m", "bot" ]
