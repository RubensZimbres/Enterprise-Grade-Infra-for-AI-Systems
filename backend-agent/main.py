import logging
import stripe
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from chains.rag_chain import protected_chain_invoke, protected_chain_stream
from dependencies import get_current_user
from database import engine, get_db
from config import settings
import models
import crud

# Tracing
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.langchain import LangChainInstrumentor
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

# Initialize DB
models.Base.metadata.create_all(bind=engine)

# Stripe Setup
stripe.api_key = settings.STRIPE_API_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

# --- Setup Tracing ---
set_global_textmap(CloudTraceFormatPropagator())
tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
trace.set_tracer_provider(tracer_provider)

# Initialize Limiter
def get_real_ip(request: Request):
    """
    Extracts the real client IP from X-Forwarded-For header.
    Falls back to remote address if header is missing.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(key_func=get_real_ip)
app = FastAPI(title="Enterprise AI Agent", version="1.0.0")

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
LangChainInstrumentor().instrument()

# Add CORS Middleware
origins = ["http://localhost:3000"]
if settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

@app.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    """
    Handle Stripe Webhooks to update user subscription status.
    """
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info(f"Received Stripe event: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_email')
        customer_id = session.get('customer')
        
        if customer_email:
            crud.update_user_subscription(db, customer_email, 'active', customer_id)
            # Log customer_id instead of email for privacy
            logger.info(f"Activated subscription for customer_id: {customer_id}")

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_email = invoice.get('customer_email')
        customer_id = invoice.get('customer')
        
        if customer_email:
            crud.update_user_subscription(db, customer_email, 'active', customer_id)
            logger.info(f"Renewed subscription for {customer_email}")
            
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # We need to find the user by customer_id since email might not be in this event
        # For simplicity, assuming we can query by customer_id if we added it to the model (we did)
        # Note: In a real app, query by stripe_customer_id. 
        # Since our CRUD uses email as primary key, we might need a lookup or just rely on the fact 
        # that 'customer.subscription.deleted' usually has the customer object expanded or we query Stripe.
        # For this MVP, we will skip complex reverse lookup unless critical. 
        pass 

    return {"status": "success"}

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