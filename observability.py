"""
Observability module for Knowledge Assistant API
Provides structured logging, metrics, and request tracing
"""
import logging
import json
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextvars import ContextVar
from functools import wraps
import uuid

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

# Metrics storage (in-memory for simplicity, use Prometheus in production)
class Metrics:
    def __init__(self):
        self.requests_total = 0
        self.requests_by_endpoint = {}
        self.requests_by_status = {}
        self.response_times = []
        self.errors_total = 0
        self.tokens_input_total = 0
        self.tokens_output_total = 0
        self.tokens_total = 0
    
    def record_request(self, endpoint: str, status_code: int, duration: float, tokens_input: int = 0, tokens_output: int = 0):
        self.requests_total += 1
        self.requests_by_endpoint[endpoint] = self.requests_by_endpoint.get(endpoint, 0) + 1
        self.requests_by_status[status_code] = self.requests_by_status.get(status_code, 0) + 1
        self.response_times.append(duration)
        self.tokens_input_total += tokens_input
        self.tokens_output_total += tokens_output
        self.tokens_total += (tokens_input + tokens_output)
        
        if status_code >= 400:
            self.errors_total += 1
    
    def get_metrics(self) -> dict:
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "requests_total": self.requests_total,
            "requests_by_endpoint": self.requests_by_endpoint,
            "requests_by_status": self.requests_by_status,
            "errors_total": self.errors_total,
            "tokens_input_total": self.tokens_input_total,
            "tokens_output_total": self.tokens_output_total,
            "tokens_total": self.tokens_total,
            "estimated_cost_usd": self._estimate_cost(),
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "p95_response_time_ms": self._percentile(95) if self.response_times else 0,
            "p99_response_time_ms": self._percentile(99) if self.response_times else 0
        }

    def _estimate_cost(self) -> float:
        """Estimate cost based on gpt-4o-mini pricing: $0.150/1M input, $0.600/1M output"""
        input_cost = (self.tokens_input_total / 1_000_000) * 0.150
        output_cost = (self.tokens_output_total / 1_000_000) * 0.600
        return round(input_cost + output_cost, 4)
    
    def _percentile(self, p: int) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * p / 100)
        return round(sorted_times[index] * 1000, 2)

metrics = Metrics()

# Structured JSON logger
class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def _log(self, level: str, message: str, **kwargs):
        request_id = request_id_var.get()
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "request_id": request_id,
            **kwargs
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_entry))
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)

logger = StructuredLogger("knowledge_assistant")

# Request tracing decorator
def trace_request(endpoint_name: str):
    """Decorator to trace API requests with timing and logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate request ID
            request_id = str(uuid.uuid4())
            request_id_var.set(request_id)
            
            start_time = time.time()
            status_code = 200
            error = None
            
            logger.info(
                f"Request started: {endpoint_name}",
                endpoint=endpoint_name,
                method="POST" if "ask" in endpoint_name or "upload" in endpoint_name else "GET"
            )
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                status_code = getattr(e, 'status_code', 500)
                logger.error(
                    f"Request failed: {endpoint_name}",
                    endpoint=endpoint_name,
                    error=error,
                    status_code=status_code
                )
                raise
            finally:
                duration = time.time() - start_time
                
                # Extract token counts if this is the /ask endpoint
                tokens_input = 0
                tokens_output = 0
                if endpoint_name == "ask_question" and not error:
                    try:
                        # Access result from the wrapped function if available
                        tokens_input = getattr(result, 'tokens_input', 0)
                        tokens_output = getattr(result, 'tokens_output', 0)
                    except:
                        pass
                
                metrics.record_request(endpoint_name, status_code, duration, tokens_input, tokens_output)
                
                logger.info(
                    f"Request completed: {endpoint_name}",
                    endpoint=endpoint_name,
                    status_code=status_code,
                    duration_ms=round(duration * 1000, 2),
                    error=error
                )
        
        return wrapper
    return decorator

def log_agent_execution(question: str, answer: str, confidence: float, sources_count: int):
    """Log agent execution details for explainability"""
    logger.info(
        "Agent execution completed",
        question_length=len(question),
        answer_length=len(answer),
        confidence_score=confidence,
        sources_count=sources_count,
        component="agent"
    )

def log_retrieval(query: str, results_count: int, top_score: float):
    """Log retrieval details"""
    logger.info(
        "Retrieval completed",
        query_length=len(query),
        results_count=results_count,
        top_score=round(top_score, 4),
        component="retrieval"
    )
