# Python base-image version. Bump manually; Dependabot's Docker ecosystem
# can't parse FROM image:${ARG}-tag patterns, so no auto-PR will arrive here.
ARG PY=3.14

FROM python:${PY}-slim AS builder
ARG PY
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VERSION=2.2.0
WORKDIR /app
RUN pip install --no-cache-dir poetry==$POETRY_VERSION && poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock ./
RUN poetry install --only=main --no-root
COPY src ./src

FROM python:${PY}-slim
ARG PY
LABEL org.opencontainers.image.source="https://github.com/{{OWNER}}/{{SERVICE}}-mcp"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser
COPY --from=builder /usr/local/lib/python${PY}/site-packages /usr/local/lib/python${PY}/site-packages
COPY --from=builder /app/src /app/src
WORKDIR /app
RUN chown -R mcpuser:mcpuser /app
USER mcpuser
EXPOSE 8080
ENTRYPOINT ["python", "src/main.py"]
