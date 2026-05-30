# Stage 1: Build the React UI
FROM node:20-alpine AS ui-build
WORKDIR /build
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

COPY --from=ui-build /build/dist ui/dist

CMD ["uv", "run", "python", "-m", "fx_agent", "--mode", "server"]
