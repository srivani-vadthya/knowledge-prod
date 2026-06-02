import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-3-small dimension


def get_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is not set in your .env file.")
    if not index_name:
        raise ValueError("PINECONE_INDEX_NAME is not set in your .env file.")

    pc = Pinecone(api_key=api_key)

    if not pc.has_index(index_name):
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=os.getenv("PINECONE_CLOUD", "aws"),
                region=os.getenv("PINECONE_REGION", "us-east-1"),
            ),
            timeout=60,
        )
    else:
        index_description = pc.describe_index(index_name)
        index_dimension = getattr(index_description, "dimension", None)
        if index_dimension and index_dimension != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Pinecone index '{index_name}' has dimension {index_dimension}, "
                f"but text-embedding-3-small needs {EMBEDDING_DIMENSION}. "
                "Create a new Pinecone index name in .env or delete/recreate the existing index."
            )

    return pc.Index(index_name)
