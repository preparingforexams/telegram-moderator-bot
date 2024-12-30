FROM ghcr.io/astral-sh/uv:0.5-python3.13-bookworm-slim

RUN apt-get update -qq \
    && apt-get install -yq --no-install-recommends \
        libjpeg-dev \
        libpng-dev \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        tini  \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN groupadd --system --gid 1000 app
RUN useradd --system --uid 1000 --gid app --create-home --home-dir /app app

USER 1000
WORKDIR /app

COPY [ "uv.lock", "pyproject.toml", "./" ]

RUN uv sync --locked --no-install-workspace --all-extras --no-dev

# We don't want the tests
COPY src/bot ./src/bot

RUN uv sync --locked --no-editable --all-extras --no-dev

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENV UV_NO_SYNC=true
ENTRYPOINT [ "tini", "--", "uv", "run", "-m", "bot" ]
