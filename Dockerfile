FROM python:3.9-slim AS base

ENV VIRTUAL_ENV="/venv"

FROM base AS poetry
ARG POETRY_VERSION="1.1.6"
RUN python -m venv "$VIRTUAL_ENV"
RUN python -m pip install "poetry==$POETRY_VERSION"

FROM poetry AS dependencies
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
COPY pyproject.toml poetry.lock /poetry/
RUN cd /poetry/ && poetry export --dev -f requirements.txt | "$VIRTUAL_ENV/bin/pip" install --no-deps --require-hashes -r /dev/stdin

FROM dependencies AS wheel
COPY . /src/
RUN rm -f /src/dist/*
RUN cd /src/ && poetry build -f wheel
RUN "$VIRTUAL_ENV/bin/pip" install --no-index /src/dist/*.whl

FROM base AS venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
COPY --from="wheel" "$VIRTUAL_ENV" "$VIRTUAL_ENV/"
