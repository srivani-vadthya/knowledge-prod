# Knowledge Assistant

Knowledge Assistant is a FastAPI + React application for uploading documents, indexing them into Pinecone, and asking grounded questions with OpenAI.

## Stack

- FastAPI backend in `api.py`
- React frontend in `frontend/`
- Pinecone vector search
- OpenAI embeddings and chat model

## Local Backend

```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env` if your API is not on `http://localhost:8000`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Environment Variables

Backend:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

Frontend:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ADMIN_CODE=admin123
VITE_USER_CODE=
```

## Render

`render.yaml` defines two services:

- `knowledge-assistant-api`: Python FastAPI service
- `knowledge-assistant-web`: Dockerized React service

Set `VITE_API_BASE_URL` on the web service to your deployed API URL.
Set `VITE_ADMIN_CODE` to the code admins should use on the frontend login screen.
