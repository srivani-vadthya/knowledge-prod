__all__ = ["graph"]
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain_openai import ChatOpenAI
from answer_confidence import simple_answer_confidence
from agent_tools import (
    compare_documents_tool,
    list_documents_tool,
    search_documents_tool,
    summarize_documents_tool,
)
from prompts import (
    DEFAULT_MODEL,
    FALLBACK_RESPONSE,
    CONVERSATIONAL_FALLBACK_RESPONSE,
    build_assistant_info_prompt,
    build_conversational_prompt,
    build_intent_prompt,
    build_prompt,
    build_tool_planning_prompt,
    build_verification_prompt,
    is_unavailable_answer,
    normalize_intent,
    normalize_verification,
    parse_tool_plan,
    strip_embedded_sources,
)
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class State(TypedDict):
    question: str
    memory: list[dict]
    memory_text: str
    context: str
    context_chunks: list[str]
    sources: list[dict]
    retrieval_score: float
    intent: str
    selected_tool: str
    tool_query: str
    tool_result: dict
    answer: str
    verification: str
    confidence: dict

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
)

def get_intent(state):
    existing_intent = state.get("intent", "")
    if existing_intent:
        return normalize_intent(existing_intent, state["question"])

    response = llm.invoke(build_intent_prompt(state["question"]))
    return normalize_intent(response.content, state["question"])

def format_memory(memory):
    if not memory:
        return ""

    lines = []
    for item in memory[-8:]:
        role = item.get("role", "user")
        content = (item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def plan_node(state):
    intent = get_intent(state)
    memory_text = state.get("memory_text") or format_memory(state.get("memory", []))

    if intent != "documentation_question":
        return {
            **state,
            "intent": intent,
            "memory_text": memory_text,
            "selected_tool": "none",
            "tool_query": "",
            "context": "",
            "context_chunks": [],
            "sources": [],
            "retrieval_score": 0.0,
            "tool_result": {},
        }

    response = llm.invoke(build_tool_planning_prompt(
        question=state["question"],
        memory=memory_text,
    ))
    plan = parse_tool_plan(response.content, state["question"])

    return {
        **state,
        "intent": intent,
        "memory_text": memory_text,
        "selected_tool": plan["tool"],
        "tool_query": plan["query"],
    }


def tool_node(state):
    if state.get("intent") != "documentation_question":
        return state

    existing_context = state.get("context", "")
    if existing_context and existing_context.strip():
        return state

    selected_tool = state.get("selected_tool", "search_documents")
    tool_query = state.get("tool_query") or state["question"]

    if selected_tool == "list_documents":
        result = list_documents_tool()
    elif selected_tool == "summarize_documents":
        result = summarize_documents_tool(tool_query)
    elif selected_tool == "compare_documents":
        result = compare_documents_tool(tool_query)
    else:
        result = search_documents_tool(tool_query)

    return {
        **state,
        "context": result["context"],
        "context_chunks": result["context_chunks"],
        "sources": result["sources"],
        "retrieval_score": result["retrieval_score"],
        "tool_result": result.get("tool_result", {}),
    }

def generate_node(state):
    intent = get_intent(state)
    memory_text = state.get("memory_text", "")

    if intent == "conversation":
        response = llm.invoke(build_conversational_prompt(
            question=state["question"],
            memory=memory_text,
        ))
        answer = (response.content or "").strip() or CONVERSATIONAL_FALLBACK_RESPONSE
        return {**state, "answer": answer}

    if intent == "assistant_info":
        response = llm.invoke(build_assistant_info_prompt(
            question=state["question"],
            memory=memory_text,
        ))
        answer = (response.content or "").strip() or CONVERSATIONAL_FALLBACK_RESPONSE
        return {**state, "answer": answer}

    # Check if context is empty or insufficient
    if not state["context"] or len(state["context"].strip()) < 10:
        return {**state, "answer": FALLBACK_RESPONSE}

    prompt = build_prompt(
        context=state["context"],
        question=state["question"],
        memory=memory_text,
    )
    response = llm.invoke(prompt)

    return {**state, "answer": strip_embedded_sources(response.content)}


def verify_node(state):
    if state.get("intent") != "documentation_question":
        return {
            **state,
            "verification": "not_applicable",
            "confidence": {},
            "sources": [],
        }

    answer = state.get("answer", "")
    context = state.get("context", "")
    context_chunks = state.get("context_chunks", [])
    retrieval_score = state.get("retrieval_score", 0.0)

    confidence = simple_answer_confidence(
        answer=answer,
        retrieved_chunks=context_chunks,
        retrieval_score=retrieval_score,
    )

    if is_unavailable_answer(answer):
        return {
            **state,
            "verification": "unsupported",
            "confidence": confidence,
            "sources": [],
        }

    response = llm.invoke(build_verification_prompt(
        context=context,
        question=state["question"],
        answer=answer,
    ))
    verification = normalize_verification(response.content)

    if verification != "supported":
        return {
            **state,
            "answer": FALLBACK_RESPONSE,
            "verification": verification,
            "confidence": confidence,
            "sources": [],
        }

    return {
        **state,
        "verification": verification,
        "confidence": confidence,
    }

builder = StateGraph(State)

builder.add_node("plan", plan_node)
builder.add_node("tool", tool_node)
builder.add_node("generate", generate_node)
builder.add_node("verify", verify_node)

builder.set_entry_point("plan")
builder.add_edge("plan", "tool")
builder.add_edge("tool", "generate")
builder.add_edge("generate", "verify")
builder.add_edge("verify", END)

graph = builder.compile()
