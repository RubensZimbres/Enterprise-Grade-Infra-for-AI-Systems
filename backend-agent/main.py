import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from chains.rag_chain import protected_chain_invoke, protected_chain_stream
from dependencies import get_current_user

# Tracing
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Setup Tracing ---
set_global_textmap(CloudTraceFormatPropagator())
tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
trace.set_tracer_provider(tracer_provider)

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Enterprise AI Agent", version="1.0.0")

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://CHANGE_ME_TO_YOUR_DOMAIN.com"
    ], # RESTRICTED: Match your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., max_length=10000) # Limit to 10k chars (DoS Protection)

class ChatResponse(BaseModel):
    response: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat_endpoint(request: ChatRequest, fastapi_req: Request, user_email: str = Depends(get_current_user)):
    """
    Main entry point for the Frontend Agent.
    Handles RAG, Memory, and DLP.
    """
    try:
        # FIX (IDOR): Scope the session_id to the authenticated user
        secure_session_id = f"{user_email}:{request.session_id}"

        # Invoke the chain with guardrails asynchronously
        response_text = await protected_chain_invoke(request.message, secure_session_id)
        
        return ChatResponse(response=response_text)
    
    except Exception as e:
        # Log the stack trace securely (Hidden from user)
        logger.error("Error processing request", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Processing Error")

@app.post("/stream")
@limiter.limit("60/minute")
async def stream_endpoint(request: ChatRequest, fastapi_req: Request, user_email: str = Depends(get_current_user)):
    """
    Streaming version of the chat endpoint.
    """
    try:
        secure_session_id = f"{user_email}:{request.session_id}"
        
        return StreamingResponse(
            protected_chain_stream(request.message, secure_session_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error("Error in streaming response", exc_info=True)
        raise HTTPException(status_code=500, detail="Streaming Error")

if __name__ == "__main__":
    import uvicorn
    # Listen on 0.0.0.0 because we are inside a container
    uvicorn.run(app, host="0.0.0.0", port=8080)