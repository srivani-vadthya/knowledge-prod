from fastapi import FastAPI, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from agent import graph
from pinecone_client import get_index
from openai import OpenAI
from answer_confidence import simple_answer_confidence
from ingest import ingest_document
from observability import logger, metrics, trace_request, log_agent_execution, request_id_var
from sync import sync_servicenow
from utils import load_indexed_docs, save_indexed_doc
import os
import shutil
from dotenv import load_dotenv
from typing import Optional, List
import time
import uuid

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Assistant API",
    description="Enterprise Knowledge Assistant API for multi-platform integration",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="The question to ask (1-1000 characters)")
    user_id: Optional[str] = Field(None, max_length=100, description="Optional user identifier")
    platform: Optional[str] = Field(None, max_length=50, description="Optional platform identifier")
    
    @validator('question')
    def validate_question(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Question cannot be empty or whitespace only")
        if len(v.strip()) < 2:
            raise ValueError("Question must be at least 2 characters long")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("User ID cannot be empty if provided")
        return v.strip() if v else None
    
    @validator('platform')
    def validate_platform(cls, v):
        if v is not None:
            allowed_platforms = ['teams', 'slack', 'whatsapp', 'web', 'mobile', 'api', 'test']
            if v.lower() not in allowed_platforms:
                raise ValueError(f"Platform must be one of: {', '.join(allowed_platforms)}")
            return v.lower()
        return None

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the best practices for Java?",
                "user_id": "user123",
                "platform": "teams"
            }
        }

class SourceInfo(BaseModel):
    document: str
    page: Optional[int] = None
    relevance_score: float

class QuestionResponse(BaseModel):
    answer: str
    status: str
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Answer quality confidence (0-1)")
    confidence_category: str = Field(..., description="HIGH, GOOD, MODERATE, or LOW")
    is_from_documents: bool = Field(..., description="Whether answer is from indexed documents")
    sources: List[SourceInfo] = Field(default_factory=list, description="Source documents used")
    user_id: Optional[str] = None
    intent: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int

class HealthResponse(BaseModel):
    status: str
    message: str

class ExecuteRequest(BaseModel):
    query: str
    limit: Optional[int] = None

class ExecuteResponse(BaseModel):
    result: dict  # Dynamic output payload as per their spec

def estimate_tokens(text: str) -> int:
    """Rough token estimate for admin usage metrics."""
    return max(1, len((text or "").strip()) // 4) if text else 0

# Exception handler for validation errors
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors with 400 Bad Request"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "status_code": 400
        }
    )

# API Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Knowledge Assistant API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "ask": "/ask - POST - Ask a question",
            "health": "/health - GET - Health check"
        }
    }

@app.get("/health", response_model=HealthResponse)
@trace_request("health_check")
async def health_check():
    """Health check endpoint with system status"""
    try:
        # Check Pinecone connection
        index = get_index()
        index_stats = index.describe_index_stats()
        
        return HealthResponse(
            status="healthy",
            message=f"Knowledge Assistant API is running. Vectors indexed: {index_stats.get('total_vector_count', 0)}"
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="degraded",
            message=f"API running but issues detected: {str(e)}"
        )

@app.get("/metrics")
async def get_metrics():
    """Get API metrics"""
    return metrics.get_metrics()

@app.get("/documents")
async def get_documents():
    """Get locally tracked indexed documents"""
    documents = load_indexed_docs()
    return {
        "documents": documents,
        "count": len(documents)
    }

@app.post("/sync/servicenow")
@trace_request("sync_servicenow")
async def sync_servicenow_documents():
    """Fetch ServiceNow knowledge articles and index them into Pinecone"""
    try:
        result = sync_servicenow()
        return {"status": "success", **result}
    except Exception as e:
        logger.error("ServiceNow sync failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"ServiceNow sync failed: {str(e)}")

@app.post("/ask", response_model=QuestionResponse, responses={
    400: {"model": ErrorResponse, "description": "Bad Request - Invalid input"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"}
})
@trace_request("ask_question")
async def ask_question(request: QuestionRequest):
    """
    Ask a question to the Knowledge Assistant
    
    - **question**: The question to ask (required, 1-1000 characters)
    - **user_id**: Optional user identifier (max 100 characters)
    - **platform**: Optional platform identifier (teams, slack, whatsapp, web, mobile, api, test)
    
    Returns:
    - **answer**: AI-generated answer
    - **confidence_score**: Confidence level (0-1)
    - **sources**: List of source documents with page numbers and relevance scores
    - **status**: Request status
    
    """
    try:
        result = graph.invoke({
            "question": request.question,
            "memory": [],
            "context": "",
            "intent": "",
            "answer": "",
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0
        })
        
        answer = result["answer"]
        intent = result.get("intent", "documentation_question")
        confidence = result.get("confidence", {})
        raw_sources = result.get("sources", [])
        tokens_input = result.get("tokens_input", 0)
        tokens_output = result.get("tokens_output", 0)
        tokens_total = result.get("tokens_total", 0)
        sources = [
            SourceInfo(
                document=source.get("document", "Unknown"),
                page=source.get("page"),
                relevance_score=round(source.get("score", 0.0), 4),
            )
            for source in raw_sources[:3]
        ]
        confidence_score = confidence.get("confidence_score", 0.0)
        confidence_category = confidence.get("category", "LOW")
        is_from_documents = confidence.get("is_from_documents", False)
        
        log_agent_execution(
            request.question,
            answer,
            confidence_score,
            len(sources)
        )
        
        logger.info(
            "Token usage",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
            component="tokens"
        )
        
        return QuestionResponse(
            answer=answer,
            status="success",
            confidence_score=confidence_score,
            confidence_category=confidence_category,
            is_from_documents=is_from_documents,
            sources=sources if intent == "documentation_question" else [],
            user_id=request.user_id,
            intent=intent,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
        )
    
    except ValueError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Internal error in ask endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/upload")
@trace_request("upload_document")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document into Pinecone"""
    allowed_extensions = [".pdf", ".txt", ".docx", ".csv", ".xlsx", ".xls", ".pptx", ".ppt", ".md"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        logger.warning("Invalid file type uploaded", filename=file.filename, extension=ext)
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed_extensions}")

    upload_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    logger.info("File uploaded", filename=file.filename, size_bytes=os.path.getsize(file_path))

    try:
        vector_count = ingest_document(file_path)
        save_indexed_doc(file.filename)
        logger.info("Document indexed successfully", filename=file.filename, chunks=vector_count)
        return {"status": "success", "filename": file.filename, "chunks_indexed": vector_count}
    except Exception as e:
        logger.error("Ingestion failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/execute")
@trace_request("execute_agent")
async def execute_agent(request: ExecuteRequest):
    """
    Trigger Agent Node Action - Marketplace compatible endpoint
    """
    try:
        result = graph.invoke({
            "question": request.query,
            "memory": [],
            "context": "",
            "intent": "",
            "answer": "",
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0
        })
        
        answer = result["answer"]
        intent = result.get("intent", "documentation_question")
        confidence = result.get("confidence", {})
        tokens_input = result.get("tokens_input", 0)
        tokens_output = result.get("tokens_output", 0)
        tokens_total = result.get("tokens_total", 0)
        sources = [
            {
                "document": source.get("document", "Unknown"),
                "page": source.get("page"),
                "relevance_score": round(source.get("score", 0.0), 4),
            }
            for source in result.get("sources", [])[:3]
        ]
        
        logger.info(
            "Token usage for execute",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
            component="tokens"
        )

        return {
            "status": "success",
            "answer": answer,
            "confidence_score": confidence.get("confidence_score", 0.0),
            "confidence_category": confidence.get("category", "LOW"),
            "is_from_documents": confidence.get("is_from_documents", False),
            "sources": sources if intent == "documentation_question" else [],
            "metadata": {
                "explanation": confidence.get("explanation", ""),
                "intent": intent,
                "selected_tool": result.get("selected_tool"),
                "verification": result.get("verification"),
                "total_chunks_retrieved": len(result.get("context_chunks", [])),
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "tokens_total": tokens_total
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "answer": "An error occurred while processing your request.",
            "sources": []
        }


# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
