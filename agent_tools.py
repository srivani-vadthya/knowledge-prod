from utils import load_indexed_docs
from rag import search_knowledge_base


def list_documents_tool() -> dict:
    documents = load_indexed_docs()
    if not documents:
        context = "No indexed documents are currently listed."
    else:
        context = "Indexed documents:\n" + "\n".join(f"- {document}" for document in documents)

    return {
        "context": context,
        "context_chunks": [context],
        "sources": [],
        "retrieval_score": 1.0 if documents else 0.0,
        "tool_result": {
            "documents": documents,
            "count": len(documents),
        },
    }


def search_documents_tool(query: str, top_k: int = 5) -> dict:
    return search_knowledge_base(query=query, top_k=top_k)


def summarize_documents_tool(query: str, top_k: int = 8) -> dict:
    result = search_knowledge_base(query=query, top_k=top_k)
    result["tool_result"] = {
        "summary_scope": query,
        "chunks_used": len(result.get("context_chunks", [])),
    }
    return result


def compare_documents_tool(query: str, top_k: int = 10) -> dict:
    result = search_knowledge_base(query=query, top_k=top_k)
    result["tool_result"] = {
        "comparison_scope": query,
        "chunks_used": len(result.get("context_chunks", [])),
    }
    return result
