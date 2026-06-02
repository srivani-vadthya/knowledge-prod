import re
from typing import Iterable


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "i", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "was", "were", "will", "with",
    "you", "your",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", _normalize(text))
    return [word for word in words if word not in STOPWORDS and len(word) > 2]


def _token_overlap(answer_tokens: list[str], chunk_tokens: set[str]) -> float:
    if not answer_tokens or not chunk_tokens:
        return 0.0
    matched = sum(1 for token in answer_tokens if token in chunk_tokens)
    return matched / len(answer_tokens)


def _phrase_overlap(answer: str, chunks: Iterable[str]) -> float:
    answer_norm = _normalize(answer)
    if not answer_norm:
        return 0.0

    answer_phrases = [
        phrase.strip()
        for phrase in re.split(r"[.!?;,\n]+", answer_norm)
        if len(phrase.strip()) >= 24
    ]
    if not answer_phrases:
        return 0.0

    chunk_text = " ".join(_normalize(chunk) for chunk in chunks)
    if not chunk_text:
        return 0.0

    matched_phrases = sum(1 for phrase in answer_phrases if phrase in chunk_text)
    return matched_phrases / len(answer_phrases)


def _coverage(answer: str, retrieved_chunks: list[str]) -> tuple[float, float]:
    answer_tokens = _tokens(answer)
    if not answer_tokens or not retrieved_chunks:
        return 0.0, 0.0

    chunk_token_sets = [set(_tokens(chunk)) for chunk in retrieved_chunks if chunk]
    if not chunk_token_sets:
        return 0.0, 0.0

    best_overlap = max(_token_overlap(answer_tokens, token_set) for token_set in chunk_token_sets)
    union_tokens = set().union(*chunk_token_sets)
    global_overlap = _token_overlap(answer_tokens, union_tokens)
    return best_overlap, global_overlap


def _category(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= 0.6:
        return "MEDIUM"
    return "LOW"


def simple_answer_confidence(answer: str, retrieved_chunks: list[str], retrieval_score: float = 0.0) -> dict:
    """
    Estimate whether the generated answer is grounded in the retrieved chunks.

    Returns:
        {
            "confidence_score": float in [0, 1],
            "category": "HIGH" | "MEDIUM" | "LOW",
            "is_from_documents": bool,
            "explanation": str,
        }
    """
    answer_norm = _normalize(answer)
    if not answer_norm:
        return {
            "confidence_score": 0.0,
            "category": "LOW",
            "is_from_documents": False,
            "explanation": "The answer is empty, so it cannot be validated against retrieved chunks.",
        }

    if not retrieved_chunks:
        return {
            "confidence_score": 0.0,
            "category": "LOW",
            "is_from_documents": False,
            "explanation": "No chunks were retrieved, so the answer could not be verified against indexed documents.",
        }

    best_overlap, global_overlap = _coverage(answer_norm, retrieved_chunks)
    phrase_overlap = _phrase_overlap(answer_norm, retrieved_chunks)
    retrieval_component = max(0.0, min(1.0, retrieval_score))

    score = (
        (0.40 * best_overlap) +
        (0.25 * global_overlap) +
        (0.20 * phrase_overlap) +
        (0.15 * retrieval_component)
    )
    score = max(0.0, min(1.0, score))
    score = round(score, 3)

    category = _category(score)
    is_from_documents = score >= 0.6

    if score >= 0.8:
        explanation = (
            "The answer strongly overlaps with the retrieved chunks and appears well grounded in the indexed documents."
        )
    elif score >= 0.6:
        explanation = (
            "The answer is reasonably supported by the retrieved chunks, though some parts may be summarized or loosely phrased."
        )
    else:
        explanation = (
            "The answer has weak overlap with the retrieved chunks, so it may be incomplete, loosely grounded, or influenced by general model knowledge."
        )

    return {
        "confidence_score": score,
        "category": category,
        "is_from_documents": is_from_documents,
        "explanation": explanation,
    }
