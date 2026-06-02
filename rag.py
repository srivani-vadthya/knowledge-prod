from openai import OpenAI
from dotenv import load_dotenv
from pinecone_client import get_index
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def search_knowledge_base(query, top_k=5):
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_vec = response.data[0].embedding
    
    index = get_index()

    results = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True
    )

    matches = results.get("matches", [])
    context_chunks = [match.get("metadata", {}).get("text", "") for match in matches]
    context = "\n".join(chunk for chunk in context_chunks if chunk)

    sources = []
    seen_docs = set()
    for match in matches:
        metadata = match.get("metadata", {})
        doc_name = metadata.get("source", "Unknown")
        page_num = metadata.get("page")
        score = match.get("score", 0.0)

        doc_key = f"{doc_name}_{page_num}"
        if doc_key not in seen_docs:
            seen_docs.add(doc_key)
            sources.append({
                "document": doc_name,
                "page": page_num,
                "score": score,
            })

    retrieval_score = matches[0].get("score", 0.0) if matches else 0.0

    return {
        "context": context,
        "context_chunks": context_chunks,
        "sources": sources,
        "retrieval_score": retrieval_score,
    }


def retrieve(query):
    result = search_knowledge_base(query)
    return result["context"]
