# Docker Guide

This project includes Docker support for both the FastAPI service and the Streamlit UI.

## Files

- `knowledge-agent/Dockerfile`
  FastAPI API container
- `knowledge-agent/Dockerfile.streamlit`
  Streamlit UI container
- `docker-compose.yml`
  Runs both services together

## Services

- API: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`

## Prerequisites

- Docker installed
- Docker Compose available
- Valid environment variables in `knowledge-agent/.env`

Required keys:

- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`

Optional keys:

- `OPENAI_MODEL`
- `PINECONE_CLOUD`
- `PINECONE_REGION`

## Run Everything

From the repo root:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up --build -d
```

## Stop Everything

```bash
docker compose down
```

## View Logs

All services:

```bash
docker compose logs -f
```

API only:

```bash
docker compose logs -f api
```

UI only:

```bash
docker compose logs -f ui
```

## Rebuild After Code Changes

```bash
docker compose up --build
```

## Run Only the API

```bash
docker compose up --build api
```

## Run Only the UI

```bash
docker compose up --build ui
```

## Notes

- Uploaded files are stored in `knowledge-agent/uploads`
- Indexed document tracking is stored in `knowledge-agent/indexed_docs.json`
- Both are mounted into containers so they persist across container restarts
- Pinecone data stays in Pinecone and is not stored locally in Docker

## Health Check

After startup, verify the API:

```bash
curl http://localhost:8000/health
```

You should get a healthy response from the FastAPI service.
