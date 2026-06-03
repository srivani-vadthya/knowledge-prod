# Docker Guide

This project includes Docker support for the FastAPI API and React web app.

## Services

- API: `http://localhost:8000`
- React UI: `http://localhost:4173`

## Required Environment

Create `.env` in the repo root with:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

## Run Everything

```bash
docker compose up --build
```

## Run Only One Service

```bash
docker compose up --build api
docker compose up --build ui
```

## Health Check

```bash
curl http://localhost:8000/health
```

The React app uses `VITE_API_BASE_URL=http://localhost:8000` in Docker Compose.
